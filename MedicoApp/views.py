from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Medico, Disponibilidad, HistorialMedico # <-- Cambiamos Evolucion por Historial
from CitaApp.models import Cita
from django.contrib import messages

@login_required
def dashboard_medico(request):
    medico = get_object_or_404(Medico, id_usuario=request.user)
    hoy = timezone.now().date()
    
    citas_hoy = Cita.objects.filter(
        id_doctor=medico, 
        fecha_hora__date=hoy
    ).order_by('fecha_hora')

    contexto = {
        'medico': medico,
        'citas': citas_hoy,
        'total_hoy': citas_hoy.count(),
    }
    return render(request, 'dashboard_medico.html', contexto)

@login_required
def mis_horarios(request):
    medico = get_object_or_404(Medico, id_usuario=request.user)
    horarios = Disponibilidad.objects.filter(id_doctor=medico).order_by('dia_semana')
    
    return render(request, 'mi_horario.html', {'horarios': horarios})

@login_required
def agenda_semanal(request):
    medico = get_object_or_404(Medico, id_usuario=request.user)
    inicio = timezone.now()
    fin = inicio + timezone.timedelta(days=7)
    
    citas_semana = Cita.objects.filter(
        id_doctor=medico,
        fecha_hora__range=(inicio, fin)
    ).order_by('fecha_hora')
    
    return render(request, 'mis_citas.html', {'citas': citas_semana})

@login_required
def historial_tratamientos(request):
    medico = get_object_or_404(Medico, id_usuario=request.user)
    
    # Ahora buscamos directamente en la tabla HistorialMedico
    # que es la que tiene la información real de lo que se hizo
    historial = HistorialMedico.objects.filter(
        id_cita__id_doctor=medico
    ).select_related('id_cita__id_paciente').order_by('-fecha_creacion')

    return render(request, 'mi_historial.html', {'historial': historial})

@login_required
def perfil_medico(request):
    medico = get_object_or_404(Medico, id_usuario=request.user)
    return render(request, 'perfil_medico.html', {'medico': medico})

@login_required
def perfil_paciente(request, paciente_id):
    from CitaApp.models import Cita
    from PacienteApp.models import Paciente
    from TratamientoApp.models import Tratamiento
    
    paciente = get_object_or_404(Paciente, id_paciente=paciente_id)
    # Traemos todos los registros de HistorialMedico de este paciente
    historiales = HistorialMedico.objects.filter(id_cita__id_paciente=paciente).order_by('-fecha_creacion')
    
    # Para el formulario del modal
    tratamientos = Tratamiento.objects.all()
    
    # Buscamos si tiene una cita hoy para "cerrarla" con el registro
    cita_actual = Cita.objects.filter(
    id_paciente=paciente, 
    id_estado_cita__nombre_estado='Pendiente'
    ).first()
    
    return render(request, 'perfil_paciente.html', {
        'paciente': paciente,
        'historiales': historiales,
        'tratamientos': tratamientos,
        'cita_actual': cita_actual
    })

@login_required
def guardar_atencion(request):
    if request.method == 'POST':
        # Obtenemos los datos del formulario manual o del ModelForm
        id_cita = request.POST.get('id_cita')
        diagnostico = request.POST.get('diagnostico')
        id_tratamiento = request.POST.get('id_tratamiento')
        observaciones = request.POST.get('observaciones_clinicas')
        costo = request.POST.get('costo_aplicado')

        # Buscamos la cita para asociarla
        cita = get_object_or_404(Cita, id_cita=id_cita)

        # Creamos el registro en HistorialMedico
        HistorialMedico.objects.create(
            id_cita=cita,
            id_tratamiento_id=id_tratamiento,
            diagnostico=diagnostico,
            observaciones_clinicas=observaciones,
            costo_aplicado=costo,
            completado=True
        )

        # Opcional: Cambiamos el estado de la cita a 'Finalizada' (ejemplo ID 3)
        cita.id_estado_cita_id = 3 
        cita.save()

        messages.success(request, "¡Atención registrada con éxito!")
        return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)
    
    return redirect('dashboard_medico')