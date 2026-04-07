from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Paciente 
from MedicoApp.models import HistorialMedico 
from CitaApp.models import Cita
from django.contrib.auth.password_validation import validate_password
from CuentasApp.forms import EditarPerfilPacienteForm
from django.core.exceptions import ValidationError

@login_required
def perfil_paciente(request):
    # Seguridad: Solo pacientes
    if request.user.id_rol.nombre_rol != 'Paciente':
        messages.warning(request, "No tienes permisos para acceder a esta sección.")
        return redirect('home')

    paciente = get_object_or_404(Paciente, id_usuario=request.user)
    
    # Consultas para el Dashboard
    citas_proximas = Cita.objects.filter(
        id_paciente=paciente, 
        fecha_hora__gte=timezone.now()
    ).order_by('fecha_hora')
    
    historial = HistorialMedico.objects.filter(
        id_cita__id_paciente=paciente
    ).order_by('-fecha_creacion')

    if request.method == 'POST':
        form = EditarPerfilPacienteForm(
            request.POST, 
            instance=request.user, 
            paciente_instance=paciente
        )
        if form.is_valid():
            # El form.save debe manejar update_session_auth_hash si cambia password
            form.save(request=request) 
            messages.success(request, "¡Perfil actualizado correctamente!")
            # Redirigir es vital para evitar re-envío de formulario al refrescar
            return redirect('perfil_paciente')
        else:
            # Imprimimos errores en consola para debugging si es necesario
            print(form.errors)
            messages.error(request, "Por favor, corrige los errores señalados.")
    else:
        form = EditarPerfilPacienteForm(
            instance=request.user, 
            paciente_instance=paciente
        )

    return render(request, 'PacienteApp/perfil.html', {
        'form': form,
        'citas_proximas': citas_proximas,
        'historial': historial
    })