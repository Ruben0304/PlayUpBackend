from fastapi import UploadFile
from infrastructure.digitalocean_client import DigitalOceanClient

class FileService:
    def __init__(self):
        self.do_client = DigitalOceanClient()

    async def upload_to_spaces(self, file: UploadFile) -> str:
        try:
            content = await file.read()
            if len(content) > 10 * 1024 * 1024:  # 10MB limit
                raise ValueError("File size exceeds 10MB limit")

            return self.do_client.upload_file(content, file.filename)

        except Exception as e:
            raise RuntimeError(f"File upload failed: {str(e)}")
        finally:
            await file.close()