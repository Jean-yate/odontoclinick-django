from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.utils import timezone
from .models import Medico, Disponibilidad, HistorialMedico
from FacturacionApp.models import Pago, MetodoPago
from CitaApp.models import Cita, EstadoCita
from PacienteApp.models import Paciente
from TratamientoApp.models import Tratamiento
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
    # 1. Buscamos al médico (usando el OneToOneField que definimos)
    medico = get_object_or_404(Medico, id_usuario=request.user)
    
    # 2. Definimos el rango: Desde el inicio de hoy hasta dentro de 7 días
    hoy_inicio = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    fin = hoy_inicio + timezone.timedelta(days=7)
    
    # 3. Filtramos y usamos select_related para que la base de datos no sufra
    citas_semana = Cita.objects.filter(
        id_doctor=medico,
        fecha_hora__range=(hoy_inicio, fin)
    ).select_related('id_paciente__id_usuario', 'id_estado_cita').order_by('fecha_hora')
    
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
    paciente = get_object_or_404(Paciente, id_paciente=paciente_id)
    # Usamos select_related para que el perfil cargue rápido sin muchas consultas a la DB
    citas = Cita.objects.filter(id_paciente=paciente).select_related('id_doctor__id_usuario', 'id_estado_cita').order_by('-fecha_hora')
    tratamientos = Tratamiento.objects.all()

    # Detectar si hay una cita para atender HOY con este doctor
    cita_actual = citas.filter(
        id_doctor__id_usuario=request.user,
        id_estado_cita__nombre_estado__in=['Confirmada', 'En Proceso']
    ).first()

    return render(request, 'perfil_paciente.html', {
        'paciente': paciente,
        'citas': citas,
        'cita_actual': cita_actual,
        'tratamientos': tratamientos,
        'hoy': timezone.now().date()
    })

@login_required
def guardar_atencion(request):
    if request.method == 'POST':
        id_cita = request.POST.get('id_cita')
        id_tratamiento_val = request.POST.get('id_tratamiento')
        diagnostico = request.POST.get('diagnostico')
        sintomas = request.POST.get('sintomas')
        plan_tratamiento = request.POST.get('plan_tratamiento')
        observaciones = request.POST.get('observaciones_clinicas')
        costo_raw = request.POST.get('costo_aplicado', '0')
        try:
            costo = Decimal(costo_raw.strip()) if costo_raw and costo_raw.strip() else Decimal('0.00')
        except (ValueError, TypeError, Exception):
            costo = Decimal('0.00')

        cita = get_object_or_404(Cita, id_cita=id_cita)
        tratamiento = get_object_or_404(Tratamiento, id_tratamiento=id_tratamiento_val)
        historial, created_h = HistorialMedico.objects.update_or_create(
            id_cita=cita,
            defaults={
                'id_tratamiento': tratamiento,
                'diagnostico': diagnostico,
                'sintomas': sintomas,
                'plan_tratamiento': plan_tratamiento,
                'observaciones_clinicas': observaciones,
                'costo_aplicado': costo,
                'completado': True
            }
        )

        estado_fin = EstadoCita.objects.filter(nombre_estado__iexact='Finalizada').first()
        if estado_fin:
            cita.id_estado_cita = estado_fin
            cita.save()
        metodo_defecto = MetodoPago.objects.first()

        if not metodo_defecto:
            metodo_defecto, _ = MetodoPago.objects.get_or_create(nombre_metodo="Pendiente", activo=1)

        pago, created_p = Pago.objects.update_or_create(
            id_cita=cita,
            defaults={
                'monto': historial.costo_aplicado, 
                'fecha_pago': timezone.now(),
                'id_metodo_pago': metodo_defecto,
                'referencia': f"PENDIENTE-CITA-{cita.id_cita}",
                'notas': f"Orden generada tras consulta médica. Dr: {request.user.nombre}"
            }
        )

        tipo_accion = "registrada" if created_h else "actualizada"
        messages.success(request, f"¡Atención {tipo_accion}! Se ha generado/sincronizado el cobro por ${historial.costo_aplicado}.")
        
        return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)
    
    return redirect('dashboard_medico')

@login_required
def iniciar_atencion(request, cita_id):
    cita = get_object_or_404(Cita, id_cita=cita_id)
    
    try:
        # Buscamos el objeto del estado 'En Proceso'
        estado_en_proceso = EstadoCita.objects.get(nombre_estado='En Proceso')
        cita.id_estado_cita = estado_en_proceso
        cita.save()
        messages.info(request, f"La consulta con {cita.id_paciente} ha iniciado.")
    except EstadoCita.DoesNotExist:
        messages.error(request, "Error: El estado 'En Proceso' no está creado en la base de datos.")
    
    # Regresamos al perfil del paciente
    return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)