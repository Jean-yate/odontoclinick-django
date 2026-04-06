from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
from django.views.decorators.http import require_POST

# Importación de modelos propios y de otras Apps
from .models import Medico, Disponibilidad, HistorialMedico
from CitaApp.models import Cita, EstadoCita
from PacienteApp.models import Paciente
from TratamientoApp.models import Tratamiento, TratamientoProducto
from InventarioApp.models import Producto, MovimientoInventario

# --- VISTAS DE PANEL Y GESTIÓN ---

@login_required
def dashboard_medico(request):
    """Visualiza el resumen diario del médico y sus citas próximas."""
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
    """Gestiona la visualización y creación de jornadas de disponibilidad."""
    medico = get_object_or_404(Medico, id_usuario=request.user)

    if request.method == 'POST':
        Disponibilidad.objects.create(
            id_medico=medico,
            dia_semana=request.POST.get('dia_semana'),
            hora_inicio=request.POST.get('hora_inicio'),
            hora_fin=request.POST.get('hora_fin'),
            duracion_cita=request.POST.get('duracion_cita')
        )
        messages.success(request, "✅ Jornada de atención agregada correctamente.")
        return redirect('mis_horarios')

    horarios = Disponibilidad.objects.filter(id_medico=medico).order_by('dia_semana', 'hora_inicio')
    return render(request, 'mi_horario.html', {'horarios': horarios})

@login_required
def eliminar_horario(request, horario_id):
    """Elimina una franja de disponibilidad específica."""
    horario = get_object_or_404(Disponibilidad, id_disponibilidad=horario_id, id_medico__id_usuario=request.user)
    horario.delete()
    messages.warning(request, "Jornada eliminada del sistema.")
    return redirect('mis_horarios')

# --- VISTAS DE AGENDA Y PACIENTES ---

@login_required
def agenda_semanal(request):
    """Muestra las citas programadas para los próximos 7 días, excluyendo canceladas."""
    medico = get_object_or_404(Medico, id_usuario=request.user)
    
    # Definimos el rango de tiempo
    hoy_inicio = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    fin = hoy_inicio + timezone.timedelta(days=7)
    
    # Filtramos y EXCLUIMOS las citas canceladas
    citas_semana = Cita.objects.filter(
        id_doctor=medico,
        fecha_hora__range=(hoy_inicio, fin)
    ).exclude(
        id_estado_cita__nombre_estado__icontains='Cancelada'  # <--- Filtro de exclusión
    ).select_related('id_paciente__id_usuario', 'id_estado_cita').order_by('fecha_hora')
    
    return render(request, 'mis_citas.html', {'citas': citas_semana})

@login_required
def perfil_paciente(request, paciente_id):
    """Muestra el expediente del paciente, historial de citas y atención actual."""
    
    # CAMBIO AQUÍ: Agregamos select_related('id_usuario')
    paciente = get_object_or_404(
        Paciente.objects.select_related('id_usuario'), 
        id_paciente=paciente_id
    )
    
    # El resto del código se mantiene igual...
    citas = Cita.objects.filter(id_paciente=paciente).select_related(
        'id_doctor__id_usuario', 'id_estado_cita'
    ).prefetch_related('historial').order_by('-fecha_hora')

    tratamientos = Tratamiento.objects.filter(activo=1)
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

# --- LÓGICA DE ATENCIÓN CLÍNICA E INVENTARIO ---

@login_required
def iniciar_atencion(request, cita_id):
    """Cambia el estado de la cita a 'En Proceso' para comenzar la consulta."""
    cita = get_object_or_404(Cita, id_cita=cita_id)
    estado_en_proceso = EstadoCita.objects.filter(nombre_estado__iexact='En Proceso').first()
    
    if estado_en_proceso:
        cita.id_estado_cita = estado_en_proceso
        cita.save()
        messages.info(request, f" La consulta con {cita.id_paciente} ha iniciado.")
    
    return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)

@login_required
def guardar_atencion(request):
    """Registra el historial médico, finaliza la cita y descuenta insumos del inventario."""
    if request.method == 'POST':
        id_cita = request.POST.get('id_cita')
        id_tratamiento_val = request.POST.get('id_tratamiento')
        
        cita = get_object_or_404(Cita, id_cita=id_cita)
        tratamiento = get_object_or_404(Tratamiento, id_tratamiento=id_tratamiento_val)

        # 1. Registrar en Historial Médico
        try:
            costo = Decimal(request.POST.get('costo_aplicado', '0').strip().replace(',', '.'))
        except:
            costo = Decimal('0.00')

        HistorialMedico.objects.update_or_create(
            id_cita=cita,
            defaults={
                'id_tratamiento': tratamiento,
                'diagnostico': request.POST.get('diagnostico'),
                'sintomas': request.POST.get('sintomas'),
                'plan_tratamiento': request.POST.get('plan_tratamiento'),
                'observaciones_clinicas': request.POST.get('observaciones_clinicas'),
                'costo_aplicado': costo,
                'completado': True
            }
        )

        # 2. Lógica de Descuento de Inventario Automático
        insumos_receta = TratamientoProducto.objects.filter(id_tratamiento=tratamiento)
        for item in insumos_receta:
            producto = item.id_producto
            cantidad_a_descontar = item.cantidad_requerida
            
            # Ajuste de stock físico
            stock_anterior = producto.stock_actual
            producto.stock_actual -= cantidad_a_descontar
            producto.save()
            
            # Registro del movimiento de salida
            MovimientoInventario.objects.create(
                producto=producto,
                id_usuario=request.user,
                tipo_movimiento='SALIDA',
                cantidad=int(cantidad_a_descontar),
                stock_anterior=stock_anterior,
                stock_nuevo=producto.stock_actual,
                motivo=f"Consumo automático: Cita #{cita.id_cita} ({tratamiento.nombre_tratamiento})"
            )

        # 3. Finalizar estado de la cita
        estado_fin = EstadoCita.objects.filter(nombre_estado__iexact='Finalizada').first()
        if estado_fin:
            cita.id_estado_cita = estado_fin
            cita.save()

        messages.success(request, "✅ Atención guardada e inventario actualizado.")
        return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)
    
    return redirect('dashboard_medico')

# --- MOTOR DE DISPONIBILIDAD (AJAX) ---

def obtener_slots_ajax(request):
    """Genera slots de tiempo disponibles para reserva de citas vía AJAX."""
    try:
        fecha_str = request.GET.get('fecha')
        doctor_id = request.GET.get('doctor_id')
        
        if not fecha_str or not doctor_id:
            return JsonResponse({'slots': []})

        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        # Django weekday: 0=Lunes, 6=Domingo. Si tu BD usa 1=Lunes, esto está bien:
        dia_bd = fecha_obj.weekday() + 1 

        horario = Disponibilidad.objects.filter(
            id_medico_id=doctor_id, 
            dia_semana=dia_bd, 
            activo=True
        ).first()
        
        if not horario:
            return JsonResponse({'slots': []})

        # --- CAMBIO CRÍTICO AQUÍ ---
        # Filtramos las citas ocupadas EXCLUYENDO las que tengan estado "Cancelada"
        citas_ocupadas = Cita.objects.filter(
            id_doctor_id=doctor_id, 
            fecha_hora__date=fecha_obj
        ).exclude(
            id_estado_cita__nombre_estado__icontains='Cancelada'
        ).values_list('fecha_hora', flat=True)
        # ---------------------------

        horas_bloqueadas = [cita.strftime('%H:%M') for cita in citas_ocupadas]

        slots = []
        # Combinamos la fecha seleccionada con las horas de la jornada del médico
        inicio = datetime.combine(fecha_obj, horario.hora_inicio)
        fin = datetime.combine(fecha_obj, horario.hora_fin)
        intervalo = horario.duracion_cita

        # Generar los slots basados en la duración configurada (ej. 20, 30 o 45 min)
        while inicio + timedelta(minutes=intervalo) <= fin:
            slot_str = inicio.strftime('%H:%M')
            if slot_str not in horas_bloqueadas:
                slots.append(slot_str)
            inicio += timedelta(minutes=intervalo)

        return JsonResponse({'slots': slots})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# --- PERFIL Y OTROS ---

@login_required
def historial_tratamientos(request):
    """Muestra el histórico de todos los tratamientos realizados por el médico."""
    medico = get_object_or_404(Medico, id_usuario=request.user)
    historial = HistorialMedico.objects.filter(
        id_cita__id_doctor=medico
    ).select_related('id_cita__id_paciente').order_by('-fecha_creacion')
    return render(request, 'mi_historial.html', {'historial': historial})

@login_required
def perfil_medico(request):
    """Visualiza la información profesional del médico logueado."""
    medico = get_object_or_404(Medico, id_usuario=request.user)
    return render(request, 'perfil_medico.html', {'medico': medico})

@login_required
def editar_perfil_medico(request):
    """Permite actualizar datos de contacto y profesionales del médico."""
    medico = get_object_or_404(Medico, id_usuario=request.user)
    if request.method == 'POST':
        user = request.user
        user.telefono = request.POST.get('telefono')
        user.save()
        
        medico.anos_experiencia = request.POST.get('experiencia')
        medico.licencia_medica = request.POST.get('licencia')
        medico.save()
        
        messages.success(request, "¡Perfil actualizado correctamente!")
        return redirect('perfil_medico')
    return render(request, 'editar_perfil_medico.html', {'medico': medico})

@login_required
def editar_horario(request, horario_id):
    """Actualiza una jornada de disponibilidad existente."""
    horario = get_object_or_404(
        Disponibilidad, 
        id_disponibilidad=horario_id, 
        id_medico__id_usuario=request.user
    )
    
    if request.method == 'POST':
        try:
            # Actualizamos los campos desde el POST
            horario.dia_semana = request.POST.get('dia_semana')
            horario.hora_inicio = request.POST.get('hora_inicio')
            horario.hora_fin = request.POST.get('hora_fin')
            horario.duracion_cita = request.POST.get('duracion_cita')
            horario.save()
            messages.success(request, "✅ Jornada actualizada con éxito.")
        except Exception as e:
            messages.error(request, f"❌ Error al actualizar: {str(e)}")
            
    return redirect('mis_horarios')

@login_required
def eliminar_horario(request, horario_id):
    """Elimina una franja de disponibilidad con validación de seguridad."""
    horario = get_object_or_404(
        Disponibilidad, 
        id_disponibilidad=horario_id, 
        id_medico__id_usuario=request.user
    )
    
    if request.method == 'POST':
        dia_nombre = horario.get_dia_semana_display()
        horario.delete()
        messages.warning(request, f"🗑️ Se ha eliminado la jornada del día {dia_nombre}.")
    
    return redirect('mis_horarios')


@login_required
@require_POST
def toggle_disponibilidad(request, horario_id):
    """Cambia el estado activo/inactivo vía AJAX."""
    horario = get_object_or_404(
        Disponibilidad, 
        id_disponibilidad=horario_id, 
        id_medico__id_usuario=request.user
    )
    
    horario.activo = not horario.activo
    horario.save()
    
    return JsonResponse({
        'status': 'success', 
        'nuevo_estado': horario.activo,
        'mensaje': f"Jornada {'activada' if horario.activo else 'desactivada'}."
    })