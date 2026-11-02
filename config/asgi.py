"""
Configuración ASGI para soporte asíncrono en el proyecto Dulce Arte.
Expone la aplicación ASGI invocable a nivel de módulo llamada 'application'.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
