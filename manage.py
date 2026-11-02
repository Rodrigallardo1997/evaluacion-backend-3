#!/usr/bin/env python
"""
Utilidad de línea de comandos de Django para tareas administrativas en Dulce Arte.
Permite ejecutar migraciones, tests, seed de datos y el servidor de desarrollo.
"""
import os
import sys


def main():
    """Ejecuta tareas administrativas de Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. Asegúrate de tenerlo instalado y "
            "con el entorno virtual activado."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
