from fastapi import UploadFile, HTTPException
from PIL import Image
import io

class ImageProcessingService:

    @staticmethod
    async def process_to_exact_size(file: UploadFile, width: int, height: int) -> bytes:
        """Controlador principal para procesamiento de imágenes"""
        try:
            image_bytes = await file.read()
            processed_bytes = ImageProcessingService.process_image_exact_size(
                image_bytes=image_bytes,
                target_width=width,
                target_height=height
            )
            return processed_bytes
        except Exception as e:
            raise HTTPException(500, f"Error procesando imagen: {str(e)}")
        finally:
            await file.close()

    @staticmethod
    def process_image_exact_size(image_bytes: bytes, target_width: int, target_height: int) -> bytes:
        """Procesa la imagen a tamaño exacto manteniendo relación de aspecto"""

        # Abrir imagen desde bytes
        with Image.open(io.BytesIO(image_bytes)) as img:

            # Convertir a RGB si es necesario
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background

            # Calcular nuevas dimensiones
            original_width, original_height = img.size
            ratio = min(target_width / original_width, target_height / original_height)
            new_size = (int(original_width * ratio), int(original_height * ratio))

            # Redimensionar y aplicar padding
            resized_img = img.resize(new_size, Image.LANCZOS)
            final_img = Image.new('RGB', (target_width, target_height), (255, 255, 255))
            offset = (
                (target_width - new_size[0]) // 2,
                (target_height - new_size[1]) // 2
            )
            final_img.paste(resized_img, offset)

            # Guardar en buffer de bytes
            img_byte_arr = io.BytesIO()
            final_img.save(img_byte_arr, format='JPEG', quality=85)

            return img_byte_arr.getvalue()