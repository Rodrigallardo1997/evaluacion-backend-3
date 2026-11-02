"""
Configuración WSGI para el servidor web en producción (Gunicorn / Nginx).
Expone la aplicación invocable a nivel de módulo llamada 'application'.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
