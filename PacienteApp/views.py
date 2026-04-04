from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Paciente 
from MedicoApp.models import HistorialMedico 
from CitaApp.models import Cita
from CuentasApp.forms import EditarPerfilPacienteForm

@login_required
def perfil_paciente(request):
    # Seguridad: Solo pacientes pueden entrar a esta vista de perfil
    if request.user.id_rol.nombre_rol != 'Paciente':
        messages.warning(request, "No tienes permisos para acceder a esta sección.")
        return redirect('home')

    # Obtenemos los datos del paciente asociados al usuario logueado
    paciente = get_object_or_404(Paciente, id_usuario=request.user)
    
    # Consultas para el Dashboard del Perfil
    citas_proximas = Cita.objects.filter(
        id_paciente=paciente, 
        fecha_hora__gte=timezone.now()
    ).order_by('fecha_hora')
    
    historial = HistorialMedico.objects.filter(
        id_cita__id_paciente=paciente
    ).order_by('-fecha_creacion')

    # Lógica del Formulario de Edición
    if request.method == 'POST':
        form = EditarPerfilPacienteForm(
            request.POST, 
            instance=request.user, 
            paciente_instance=paciente
        )
        if form.is_valid():
            # Guardamos ambos modelos (Usuario y Paciente)
            form.save(request=request) 
            messages.success(request, "¡Perfil actualizado! Tus cambios se guardaron correctamente.")
            return redirect('perfil_paciente')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        # Carga inicial con los datos actuales
        form = EditarPerfilPacienteForm(
            instance=request.user, 
            paciente_instance=paciente
        )

    return render(request, 'PacienteApp/perfil.html', {
        'form': form,
        'citas_proximas': citas_proximas,
        'historial': historial
    })