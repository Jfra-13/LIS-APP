from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView
from admision.models import Paciente
from consulta.models import NotaMedica


class PatientRequiredMixin(UserPassesTestMixin):
    """Ensures the authenticated user is a patient and may only access their own data."""

    def test_func(self):
        return Paciente.objects.filter(dni=self.request.user.username).exists()


class PatientDashboardView(LoginRequiredMixin, PatientRequiredMixin, ListView):
    model = NotaMedica
    template_name = 'portal_paciente/dashboard.html'
    context_object_name = 'notas'

    def get_queryset(self):
        return NotaMedica.objects.filter(
            paciente__dni=self.request.user.username
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paciente = get_object_or_404(Paciente, dni=self.request.user.username)
        context['paciente'] = paciente
        ai_service = AIService()
        context['ai_questions_remaining'] = ai_service.remaining(paciente)
        context['ai_max_questions'] = ai_service.max_questions
        return context


from django.http import JsonResponse
from django.views import View
from .ai_service import AIService

class AIChatView(LoginRequiredMixin, PatientRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        paciente = get_object_or_404(Paciente, dni=request.user.username)
        user_message = request.POST.get('message')
        
        if not user_message:
            return JsonResponse({'error': 'No se proporcionó mensaje'}, status=400)

        # Obtener el último diagnóstico
        last_nota = NotaMedica.objects.filter(paciente=paciente).order_by('-created_at').first()
        last_diagnosis = None
        if last_nota and last_nota.cie_short_description:
            last_diagnosis = f"{last_nota.cie_code} - {last_nota.cie_short_description}"

        ai_service = AIService()
        response = ai_service.get_response(paciente, user_message, last_diagnosis)

        return JsonResponse({
            'response': response,
            'remaining': ai_service.remaining(paciente),
        })


class RecetaDetailView(LoginRequiredMixin, PatientRequiredMixin, DetailView):
    model = NotaMedica
    template_name = 'portal_paciente/receta_detail.html'
    context_object_name = 'nota'

    def get_object(self, queryset=None):
        return get_object_or_404(
            NotaMedica,
            receta_id=self.kwargs.get('receta_id'),
            paciente__dni=self.request.user.username,
        )
