from pydantic import BaseModel

class ImageUploadRequest(BaseModel):
    folder_name: str  # Ej: "profile_images"
    target_width: int  # Ej: 800
    target_height: int  # Ej: 600
    desired_filename: str  # Ej: "user_avatar" (sin extensión)