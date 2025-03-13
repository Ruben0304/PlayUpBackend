import hashlib
import hmac
import datetime
import requests
from urllib.parse import quote
import logging

from core.config import DO_SPACES_ENDPOINT, DO_SPACES_BUCKET, DO_SPACES_REGION, DO_SPACES_SECRET, DO_SPACES_KEY

logger = logging.getLogger(__name__)

class DigitalOceanClient:
    def __init__(self):
        self.endpoint = DO_SPACES_ENDPOINT
        self.bucket = DO_SPACES_BUCKET
        self.region = DO_SPACES_REGION
        self.service = "s3"
        self.request_type = "aws4_request"

    def _sign(self, key: bytes, msg: str) -> bytes:
        """Firma un mensaje con la clave proporcionada"""
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _get_signing_key(self, date_stamp: str) -> bytes:
        """Genera la clave de firma en 4 pasos"""
        k_date = self._sign(f"AWS4{DO_SPACES_SECRET}".encode(), date_stamp)
        k_region = self._sign(k_date, self.region)
        k_service = self._sign(k_region, self.service)
        return self._sign(k_service, self.request_type)

    def _create_canonical_request(self, method: str, path: str, headers: dict, content_hash: str) -> str:
        """Crea la solicitud canónica para la firma"""
        sorted_headers = sorted(headers.items(), key=lambda x: x[0].lower())

        canonical_headers = "\n".join([f"{k.lower()}:{v}" for k, v in sorted_headers])
        signed_headers = ";".join([k.lower() for k, v in sorted_headers])

        return "\n".join([
            method,
            path,
            "",  # query string vacío
            canonical_headers,
            "",
            signed_headers,
            content_hash
        ])

    def _generate_signature(self, canonical_request: str, date_stamp: str, amz_date: str, signing_key: bytes) -> str:
        """Genera la firma final"""
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/{self.request_type}"
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode()).hexdigest()
        ])
        return hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    def upload_file(self, file_content: bytes, file_path: str) -> str:
        """Sube un archivo a Digital Ocean Spaces"""
        try:
            # 1. Preparar parámetros de fecha
            now = datetime.datetime.utcnow()
            amz_date = now.strftime("%Y%m%dT%H%M%SZ")
            date_stamp = now.strftime("%Y%m%d")

            # 2. Codificar path y crear URL
            encoded_path = quote(file_path.lstrip('/'))
            url = f"https://{self.bucket}.{self.region}.digitaloceanspaces.com/{encoded_path}"

            # 3. Calcular hash del contenido
            content_hash = hashlib.sha256(file_content).hexdigest()

            # 4. Crear headers
            headers = {
                "Content-Type": "application/octet-stream",
                "Host": f"{self.bucket}.{self.region}.digitaloceanspaces.com",
                "x-amz-acl": "public-read",
                "x-amz-content-sha256": content_hash,
                "x-amz-date": amz_date
            }

            # 5. Crear solicitud canónica
            canonical_request = self._create_canonical_request(
                method="PUT",
                path=f"/{encoded_path}",
                headers=headers,
                content_hash=content_hash
            )

            # 6. Generar firma
            signing_key = self._get_signing_key(date_stamp)
            signature = self._generate_signature(
                canonical_request=canonical_request,
                date_stamp=date_stamp,
                amz_date=amz_date,
                signing_key=signing_key
            )

            # 7. Construir headers finales
            credential_scope = f"{date_stamp}/{self.region}/{self.service}/{self.request_type}"
            signed_headers = ";".join(sorted([k.lower() for k in headers.keys()]))

            headers["Authorization"] = (
                f"AWS4-HMAC-SHA256 "
                f"Credential={DO_SPACES_KEY}/{credential_scope}, "
                f"SignedHeaders={signed_headers}, "
                f"Signature={signature}"
            )

            # 8. Enviar solicitud
            response = requests.put(
                url,
                headers=headers,
                data=file_content,
                timeout=30
            )

            if not response.ok:
                logger.error(f"Error en Digital Ocean: {response.status_code} - {response.text}")
                raise RuntimeError(f"DO Spaces error: {response.text}")

            return url

        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión: {str(e)}")
            raise RuntimeError("Error de conexión con Digital Ocean Spaces")
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
            raise
            
    def delete_file(self, file_path: str) -> bool:
        """Elimina un archivo de Digital Ocean Spaces por su ruta
        
        Args:
            file_path: Ruta del archivo a eliminar
            
        Returns:
            bool: True si se eliminó correctamente, False en caso contrario
            
        Raises:
            RuntimeError: Si ocurre un error al conectar con Digital Ocean Spaces
        """
        try:
            # 1. Preparar parámetros de fecha
            now = datetime.datetime.utcnow()
            amz_date = now.strftime("%Y%m%dT%H%M%SZ")
            date_stamp = now.strftime("%Y%m%d")
            
            # 2. Codificar path y crear URL
            encoded_path = quote(file_path.lstrip('/'))
            url = f"https://{self.bucket}.{self.region}.digitaloceanspaces.com/{encoded_path}"
            
            # 3. Crear headers básicos (sin contenido para DELETE)
            headers = {
                "Host": f"{self.bucket}.{self.region}.digitaloceanspaces.com",
                "x-amz-content-sha256": hashlib.sha256(b"").hexdigest(),
                "x-amz-date": amz_date
            }
            
            # 4. Crear solicitud canónica
            canonical_request = self._create_canonical_request(
                method="DELETE",
                path=f"/{encoded_path}",
                headers=headers,
                content_hash=hashlib.sha256(b"").hexdigest()
            )
            
            # 5. Generar firma
            signing_key = self._get_signing_key(date_stamp)
            signature = self._generate_signature(
                canonical_request=canonical_request,
                date_stamp=date_stamp,
                amz_date=amz_date,
                signing_key=signing_key
            )
            
            # 6. Construir headers finales
            credential_scope = f"{date_stamp}/{self.region}/{self.service}/{self.request_type}"
            signed_headers = ";".join(sorted([k.lower() for k in headers.keys()]))
            
            headers["Authorization"] = (
                f"AWS4-HMAC-SHA256 "
                f"Credential={DO_SPACES_KEY}/{credential_scope}, "
                f"SignedHeaders={signed_headers}, "
                f"Signature={signature}"
            )
            
            # 7. Enviar solicitud DELETE
            response = requests.delete(
                url,
                headers=headers,
                timeout=30
            )
            
            if not response.ok:
                logger.error(f"Error al eliminar archivo: {response.status_code} - {response.text}")
                return False
                
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al eliminar archivo: {str(e)}")
            raise RuntimeError("Error de conexión con Digital Ocean Spaces")
        except Exception as e:
            logger.error(f"Error inesperado al eliminar archivo: {str(e)}")
            raise