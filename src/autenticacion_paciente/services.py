import logging
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .tokens import account_activation_token

logger = logging.getLogger(__name__)

def enviar_magic_link(user, request=None):
    """
    Genera un token y envía un correo electrónico con el Magic Link al paciente.
    """
    token = account_activation_token.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Por ahora definimos una URL base. En la Fase 2 se creará la vista real.
    # Intentamos obtener el dominio del request si está disponible.
    if request:
        domain = request.get_host()
        protocol = 'https' if request.is_secure() else 'http'
    else:
        domain = 'localhost:8000' # Default para desarrollo
        protocol = 'http'

    # La URL final usando reverse
    relative_link = reverse('autenticacion_paciente:verify_link', kwargs={'uidb64': uid, 'token': token})
    link = f"{protocol}://{domain}{relative_link}"
    
    subject = "Tu enlace de acceso al Portal de Paciente"
    
    context = {
        'nombre': user.first_name or user.username,
        'link': link,
    }
    
    html_message = render_to_string('autenticacion_paciente/magic_link_email.html', context)
    plain_message = strip_tags(html_message)
    
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@applis.com')
    recipient_list = [user.email]

    try:
        send_mail(
            subject, 
            plain_message, 
            from_email, 
            recipient_list, 
            html_message=html_message
        )
        logger.info(f"Magic link enviado a {user.email}")
        return True
    except Exception as e:
        logger.error(f"Error al enviar magic link: {e}")
        return False
