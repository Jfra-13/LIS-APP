from django.urls import path

from . import views

app_name = 'admision'

urlpatterns = [
    # Listado de pacientes
    path('pacientes/', views.PacienteListView.as_view(), name='paciente_list'),
    
    # Crear nuevo paciente
    path('pacientes/nuevo/', views.PacienteCreateView.as_view(), name='paciente_create'),
    
    # Ver detalles de paciente
    path('pacientes/<uuid:pk>/', views.PacienteDetailView.as_view(), name='paciente_detail'),
    
    # Editar paciente
    path('pacientes/<uuid:pk>/editar/', views.PacienteUpdateView.as_view(), name='paciente_update'),
    
    # Eliminar paciente (soft delete)
    path('pacientes/<uuid:pk>/eliminar/', views.PacienteDeleteView.as_view(), name='paciente_delete'),
]

