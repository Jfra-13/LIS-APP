import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import FormView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.models import Group
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

from admision.models import Paciente
from .forms import RequestLoginLinkForm
from .services import enviar_magic_link
from .tokens import account_activation_token

User = get_user_model()
logger = logging.getLogger(__name__)

class RequestLoginLinkView(FormView):
    template_name = 'autenticacion_paciente/request_link.html'
    form_class = RequestLoginLinkForm
    success_url = reverse_lazy('autenticacion_paciente:link_sent')

    def form_valid(self, form):
        dni = form.cleaned_data['dni']
        try:
            paciente = Paciente.objects.get(dni=dni)
        except Paciente.DoesNotExist:
            form.add_error('dni', 'No se encontró un paciente con ese DNI.')
            return self.form_invalid(form)

        # Buscar o crear User
        user, created = User.objects.get_or_create(
            username=dni,
            defaults={
                'email': f"{dni}@applis.com", # Placeholder si no tiene email real
                'first_name': paciente.nombres,
                'last_name': paciente.apellidos,
            }
        )

        # Si el paciente tiene un email real guardado, lo usamos
        # (Asumiendo que el modelo Paciente tiene email, si no, usamos el placeholder)
        if hasattr(paciente, 'email') and paciente.email:
            user.email = paciente.email
            user.save()

        # Asignar al grupo "Pacientes"
        pacientes_group, _ = Group.objects.get_or_create(name='Pacientes')
        user.groups.add(pacientes_group)

        # Enviar magic link
        if enviar_magic_link(user, self.request):
            return super().form_valid(form)
        else:
            form.add_error(None, 'Error al enviar el correo. Inténtalo más tarde.')
            return self.form_invalid(form)

class LoginLinkSentView(TemplateView):
    template_name = 'autenticacion_paciente/link_sent.html'

class LoginFromLinkView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and account_activation_token.check_token(user, token):
            login(request, user)
            messages.success(request, f"Bienvenido, {user.get_full_name() or user.username}")
            return redirect('portal_paciente:dashboard')
        else:
            return render(request, 'autenticacion_paciente/invalid_link.html')
