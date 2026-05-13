from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .models import Paciente
from .forms import PacienteForm


class AdmisionRequiredMixin(UserPassesTestMixin):
    """Mixin que verifica que el usuario pertenece al grupo Técnicos Administrativos."""
    
    def test_func(self):
        """Verificar que el usuario está en el grupo requerido."""
        return self.request.user.groups.filter(name='Tecnicos_Administrativos').exists()
    
    def handle_no_permission(self):
        """Redirigir si el usuario no tiene permisos."""
        messages.error(
            self.request,
            'No tiene permisos para acceder a esta sección. Solo usuarios del grupo Técnicos Administrativos pueden acceder.'
        )
        return redirect('home')


class PacienteListView(AdmisionRequiredMixin, ListView):
    """Vista para listar pacientes activos."""
    
    model = Paciente
    template_name = 'admision/paciente_list.html'
    context_object_name = 'pacientes'
    paginate_by = 50
    
    def get_queryset(self):
        """
        Retorna pacientes activos con select_related.
        Permite búsqueda por DNI o nombres.
        """
        queryset = Paciente.objects.select_related('usuario_creador').filter(estado='activo')
        
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(dni__icontains=search) |
                Q(nombres__icontains=search) |
                Q(apellidos__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class PacienteCreateView(AdmisionRequiredMixin, CreateView):
    """Vista para crear un nuevo paciente."""
    
    model = Paciente
    form_class = PacienteForm
    template_name = 'admision/paciente_form.html'
    
    def form_valid(self, form):
        """Asignar usuario_creador antes de guardar."""
        form.instance.usuario_creador = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Paciente {form.instance.nombres} {form.instance.apellidos} creado exitosamente.'
        )
        return response
    
    def get_success_url(self):
        return reverse_lazy('admision:paciente_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Nuevo Paciente'
        context['button_text'] = 'Crear Paciente'
        return context


class PacienteDetailView(AdmisionRequiredMixin, DetailView):
    """Vista para ver detalles de un paciente."""
    
    model = Paciente
    template_name = 'admision/paciente_detail.html'
    context_object_name = 'paciente'
    
    def get_queryset(self):
        """Optimizar query con select_related."""
        return Paciente.objects.select_related('usuario_creador')


class PacienteUpdateView(AdmisionRequiredMixin, UpdateView):
    """Vista para editar un paciente existente."""
    
    model = Paciente
    form_class = PacienteForm
    template_name = 'admision/paciente_form.html'
    
    def form_valid(self, form):
        """No permitir cambiar usuario_creador."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Paciente {form.instance.nombres} {form.instance.apellidos} actualizado exitosamente.'
        )
        return response
    
    def get_success_url(self):
        return reverse_lazy('admision:paciente_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Paciente: {self.object.nombres} {self.object.apellidos}'
        context['button_text'] = 'Actualizar Paciente'
        return context


class PacienteDeleteView(AdmisionRequiredMixin, DeleteView):
    """Vista para eliminar un paciente (soft delete)."""
    
    model = Paciente
    template_name = 'admision/paciente_confirm_delete.html'
    success_url = reverse_lazy('admision:paciente_list')
    
    def post(self, request, *args, **kwargs):
        """Realizar soft delete en lugar de eliminar fila."""
        self.object = self.get_object()
        paciente_str = f"{self.object.nombres} {self.object.apellidos}"
        
        # Soft delete: marcar como inactivo
        self.object.estado = 'inactivo'
        self.object.save()
        
        messages.success(
            request,
            f'Paciente {paciente_str} marcado como inactivo correctamente.'
        )
        return redirect(self.success_url)

