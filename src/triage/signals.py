from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import RegistroTriage
from nlp_engine.tasks import procesar_diagnostico_cie10

@receiver(post_save, sender=RegistroTriage)
def disparar_analisis_nlp(sender, instance, created, **kwargs):
    # Solo disparamos la tarea si es un registro NUEVO y no ha sido procesado
    if created and not instance.procesado_por_ia:
        # El .delay() es la magia: envía el mensaje a RabbitMQ y no bloquea el sistema
        procesar_diagnostico_cie10.delay(instance.id, instance.notas_medico)