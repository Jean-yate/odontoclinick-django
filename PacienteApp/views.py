from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import Paciente, HistorialMedico
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
    
    historial = HistorialMedico.objects.filter(id_paciente=paciente).order_by('-fecha')

    if request.method == 'POST':
        form = EditarPerfilPacienteForm(
            request.POST, 
            instance=request.user, 
            paciente_instance=paciente
        )
        if form.is_valid():
            # PASAMOS EL REQUEST AL MÉTODO SAVE DEL FORMULARIO
            form.save(request=request) 
            
            messages.success(request, "Tus datos han sido actualizados con éxito.")
            return redirect('perfil_paciente')
        else:
            print("--- ERRORES DEL FORMULARIO ---")
            print(form.errors)
            print("------------------------------")
            messages.error(request, "Hubo un error al validar tus datos. Revisa el formulario.")
    else:
        form = EditarPerfilPacienteForm(instance=request.user, paciente_instance=paciente)

    return render(request, 'PacienteApp/perfil.html', {
        'form': form,
        'citas_proximas': citas_proximas,
        'historial': historial
    })