"""
Manejadores de almacenamiento en la nube (AWS S3) para Dulce Arte.
Permite almacenar archivos estáticos y multimedia (firmas y fotos) en AWS S3.
"""
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    """Almacenamiento de archivos estáticos (CSS, JS, Fuentes) en el bucket S3."""
    location = 'static'
    default_acl = 'public-read'


class MediaStorage(S3Boto3Storage):
    """
    Almacenamiento de archivos multimedia en el bucket S3.
    Guarda fotos de tortas, recetas, firmas digitales de despachos y comprobantes.
    """
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False
