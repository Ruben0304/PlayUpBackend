import hashlib
import hmac
import datetime
import requests
from urllib.parse import quote

from core.config import DO_SPACES_BUCKET, DO_SPACES_REGION, DO_SPACES_SECRET, DO_SPACES_KEY


class DigitalOceanClient:
    def __init__(self):
        self.host = f"{DO_SPACES_BUCKET}.{DO_SPACES_REGION}.digitaloceanspaces.com"
        self.base_url = f"https://{self.host}"

    @staticmethod
    def _sign(key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _get_signing_key(self, date_stamp):
        k_date = self._sign(f"AWS4{DO_SPACES_SECRET}".encode(), date_stamp)
        k_region = self._sign(k_date, DO_SPACES_REGION)
        k_service = self._sign(k_region, "s3")
        return self._sign(k_service, "aws4_request")

    def upload_file(self, file_content: bytes, filename: str) -> str:
        try:
            # 1. Configurar parámetros temporales
            now = datetime.datetime.utcnow()
            amz_date = now.strftime("%Y%m%dT%H%M%SZ")
            date_stamp = now.strftime("%Y%m%d")
            encoded_filename = quote(filename)

            # 2. Headers (¡Orden alfabético!)
            headers = {
                "Content-Length": str(len(file_content)),
                "Content-Type": "application/octet-stream",
                "Host": self.host,
                "x-amz-acl": "public-read",
                "x-amz-content-sha256": hashlib.sha256(file_content).hexdigest(),
                "x-amz-date": amz_date
            }

            # 3. Crear solicitud canónica (¡Igual que en Colab!)
            sorted_headers = sorted(headers.items(), key=lambda x: x[0].lower())

            canonical_request = "\n".join([
                "PUT",
                f"/{encoded_filename}",
                "",
                "\n".join([f"{k.lower()}:{v}" for k, v in sorted_headers]),
                "",
                ";".join([k.lower() for k, v in sorted_headers]),
                headers["x-amz-content-sha256"]
            ])

            # 4. Generar firma
            credential_scope = f"{date_stamp}/{DO_SPACES_REGION}/s3/aws4_request"
            string_to_sign = "\n".join([
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode()).hexdigest()
            ])

            signing_key = self._get_signing_key(date_stamp)
            signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

            # 5. Construir headers finales
            headers["Authorization"] = (
                f"AWS4-HMAC-SHA256 Credential={DO_SPACES_KEY}/{credential_scope}, "
                f"SignedHeaders={';'.join([k.lower() for k, v in sorted_headers])}, "
                f"Signature={signature}"
            )

            # 6. Enviar petición
            url = f"{self.base_url}/{encoded_filename}"
            response = requests.put(url, headers=headers, data=file_content)

            if response.status_code == 200:
                return url
            raise Exception(f"Error {response.status_code}: {response.text}")

        except Exception as e:
            raise RuntimeError(f"DO Spaces upload failed: {str(e)}")