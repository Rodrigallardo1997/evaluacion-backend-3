"""
Manejadores de almacenamiento en la nube (AWS S3) para Dulce Arte.
Compatible con buckets modernos con BucketOwnerEnforced (sin ACLs legadas).
"""
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    """Almacenamiento de archivos estáticos (CSS, JS, Fuentes) en el bucket S3."""
    location = 'static'
    default_acl = None
    querystring_auth = False


class MediaStorage(S3Boto3Storage):
    """
    Almacenamiento privado de archivos multimedia en el bucket S3.
    Guarda fotos, firmas digitales de despachos y comprobantes usando URLs prefirmadas.
    """
    location = 'media'
    default_acl = None
    file_overwrite = False
    querystring_auth = True
