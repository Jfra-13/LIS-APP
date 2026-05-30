from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Paciente

User = get_user_model()

@receiver(post_save, sender=Paciente)
def crear_usuario_paciente(sender, instance, created, **kwargs):
    """
    Crea automáticamente un usuario para el paciente cuando este es registrado.
    El username será el DNI y la contraseña inicial también será el DNI.
    """
    if created:
        # Evitar errores si el usuario ya existe (por si acaso)
        if not User.objects.filter(username=instance.dni).exists():
            User.objects.create_user(
                username=instance.dni,
                password=instance.dni,
                first_name=instance.nombres,
                last_name=instance.apellidos,
                email=instance.email
            )
