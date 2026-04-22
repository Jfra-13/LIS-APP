import os
from celery import Celery

# Establecer el módulo de configuración de Django por defecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('smart_emergency')

# Usar una cadena aquí significa que el worker no tiene que serializar
# el objeto de configuración a procesos hijos.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carga automáticamente las tareas de todas las apps registradas
app.autodiscover_tasks()