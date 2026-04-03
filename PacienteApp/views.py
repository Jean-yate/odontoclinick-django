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
    if request.user.id_rol.nombre_rol != 'Paciente':
        return redirect('home')

    paciente = get_object_or_404(Paciente, id_usuario=request.user)
    
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
            form.save(request=request) 
            messages.success(request, "Tus datos han sido actualizados con éxito.")
            return redirect('perfil_paciente')
        else:
            messages.error(request, "Hubo un error al validar tus datos. Revisa el formulario.")
    else:
        form = EditarPerfilPacienteForm(instance=request.user, paciente_instance=paciente)

    return render(request, 'PacienteApp/perfil.html', {
        'form': form,
        'citas_proximas': citas_proximas,
        'historial': historial
    })