from django.urls import path
from . import views

app_name = 'autenticacion_paciente'

urlpatterns = [
    path('solicitar/', views.RequestLoginLinkView.as_view(), name='request_link'),
    path('confirmacion/', views.LoginLinkSentView.as_view(), name='link_sent'),
    path('verificar/<uidb64>/<token>/', views.LoginFromLinkView.as_view(), name='verify_link'),
]
