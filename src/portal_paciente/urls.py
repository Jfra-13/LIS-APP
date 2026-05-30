from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import PatientLoginView, PatientDashboardView, RecetaDetailView

app_name = 'portal_paciente'

urlpatterns = [
    path('login/', PatientLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='portal_paciente:login'), name='logout'),
    path('dashboard/', PatientDashboardView.as_view(), name='dashboard'),
    path('receta/<uuid:receta_id>/', RecetaDetailView.as_view(), name='receta_detail'),
]
