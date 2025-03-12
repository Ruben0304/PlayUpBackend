from enum import Enum

class ImageSize(Enum):
    """
    Tamaños ideales para imágenes en aplicaciones móviles.
    - Fotos de perfil: Cuadradas, alta resolución.
    - Banners: Rectangulares, optimizados para pantallas móviles.
    """

    # Foto de perfil (cuadrada)
    PROFILE_PICTURE = (1080, 1080)  # 1:1 (Instagram, Facebook, etc.)

    # Banner de perfil (rectangular)
    PROFILE_BANNER = (1200, 600)  # 2:1 (Twitter, LinkedIn, etc.)

    # Banner para cabecera (rectangular)
    HEADER_BANNER = (1920, 1080)  # 16:9 (Pantallas móviles y web)

    # Banner para historias (vertical)
    STORY_BANNER = (1080, 1920)  # 9:16 (Instagram Stories, Snapchat)

    # Banner para publicaciones (cuadrado o rectangular)
    POST_BANNER = (1200, 1200)  # 1:1 (Publicaciones en redes sociales)

    # Banner para anuncios (rectangular)
    AD_BANNER = (1200, 628)  # 1.91:1 (Anuncios en Facebook)

    # Miniatura (cuadrada)
    THUMBNAIL = (500, 500)  # 1:1 (Miniaturas en listas o grids)

    @property
    def width(self):
        """Devuelve el ancho de la imagen."""
        return self.value[0]

    @property
    def height(self):
        """Devuelve el alto de la imagen."""
        return self.value[1]

    @property
    def aspect_ratio(self):
        """Devuelve la relación de aspecto (ancho/alto)."""
        return self.value[0] / self.value[1]