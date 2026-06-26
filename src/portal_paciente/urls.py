from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic.base import RedirectView

from .views import AIChatView, PatientDashboardView, RecetaDetailView

app_name = 'portal_paciente'

urlpatterns = [
    # Redirect old password-login URL to the magic-link request page.
    # Keeps the 'portal_paciente:login' name so bookmarks and existing references
    # continue to work without 404s.
    path(
        'login/',
        RedirectView.as_view(pattern_name='autenticacion_paciente:request_link', permanent=False),
        name='login',
    ),
    path(
        'logout/',
        LogoutView.as_view(next_page='autenticacion_paciente:request_link'),
        name='logout',
    ),
    path('dashboard/', PatientDashboardView.as_view(), name='dashboard'),
    path('receta/<uuid:receta_id>/', RecetaDetailView.as_view(), name='receta_detail'),
    path('ai-chat/', AIChatView.as_view(), name='ai_chat'),
]
