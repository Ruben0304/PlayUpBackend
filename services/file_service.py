from fastapi import UploadFile, HTTPException
from PIL import Image
import io
import os
from infrastructure.digitalocean_client import DigitalOceanClient
from domain.schemas.file_schema import ImageUploadRequest

class FileService:
    def __init__(self):
        self.do_client = DigitalOceanClient()

    async def process_and_upload(self, file: UploadFile, request: ImageUploadRequest) -> str:
        try:
            # Procesar imagen
            processed_image = await self._process_image(file, request)

            # Generar nombre de archivo final
            final_filename = self._generate_filename(file, request)

            # Subir a Digital Ocean
            return self.do_client.upload_file(
                processed_image,
                final_filename
            )

        except Exception as e:
            raise RuntimeError(str(e))

    async def _process_image(self, file: UploadFile, request: ImageUploadRequest) -> bytes:
        image_bytes = await file.read()

        with Image.open(io.BytesIO(image_bytes)) as img:
            # Convertir a RGB si es necesario
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background

            # Calcular relación de aspecto
            original_width, original_height = img.size
            ratio = min(request.target_width / original_width,
                        request.target_height / original_height)
            new_size = (int(original_width * ratio),
                        int(original_height * ratio))

            # Redimensionar
            resized_img = img.resize(new_size, Image.LANCZOS)

            # Crear canvas final
            final_img = Image.new('RGB',
                                  (request.target_width, request.target_height),
                                  (255, 255, 255))
            offset = ((request.target_width - new_size[0]) // 2,
                      (request.target_height - new_size[1]) // 2)
            final_img.paste(resized_img, offset)

            # Convertir a bytes
            img_byte_arr = io.BytesIO()
            final_img.save(img_byte_arr, format='JPEG', quality=85)
            return img_byte_arr.getvalue()

    def _generate_filename(self, file: UploadFile, request: ImageUploadRequest) -> str:
        # Obtener extensión original o usar jpg
        original_ext = os.path.splitext(file.filename)[1].lower()
        ext = original_ext if original_ext in ['.jpg', '.jpeg', '.png'] else '.jpg'

        # Limpiar nombre deseado
        clean_name = request.desired_filename.replace(" ", "_").lower()

        # Construir path final
        return f"{request.folder_name}/{clean_name}{ext}"