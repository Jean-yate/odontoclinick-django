from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
from django.views.decorators.http import require_POST
from decimal import Decimal
from django.db import transaction

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
    """Registra el historial médico con validaciones estrictas, finaliza la cita y descuenta insumos."""
    if request.method == 'POST':
        id_cita = request.POST.get('id_cita')
        id_tratamiento_val = request.POST.get('id_tratamiento')
        
        cita = get_object_or_404(Cita, id_cita=id_cita)
        tratamiento = get_object_or_404(Tratamiento, id_tratamiento=id_tratamiento_val)

        # ---- EXTRACCIÓN Y VALIDACIÓN DE DATOS OBLIGATORIOS ----
        diagnostico = request.POST.get('diagnostico', '').strip()
        plan_tratamiento = request.POST.get('plan_tratamiento', '').strip()
        observaciones_clinicas = request.POST.get('observaciones_clinicas', '').strip()
        sintomas = request.POST.get('sintomas', '').strip()
        costo_str = request.POST.get('costo_aplicado', '').strip()

        # 1. Verificar que ningún campo esté vacío
        if not all([diagnostico, plan_tratamiento, observaciones_clinicas, sintomas, costo_str]):
            messages.error(request, "❌ Todos los campos del registro clínico son obligatorios.")
            return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)

        # Región de expresiones regulares básicas (letras, números y espacios)
        # ^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ ]{3,}$ -> Mínimo 3 caracteres, sin caracteres especiales como @, $, *, #, etc.
        regex_letras_numeros = r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ ]{3,}$'
        
        # ^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]{3,}$ -> Mínimo 3 caracteres, solo letras y espacios (sin números)
        regex_solo_letras = r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]{3,}$'

        # 2. Validar Diagnóstico, Plan de tratamiento y Observaciones clínicas
        if not re.match(regex_letras_numeros, diagnostico):
            messages.error(request, "❌ Diagnóstico inválido: Mínimo 3 caracteres (letras/números), sin caracteres especiales.")
            return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)

        if not re.match(regex_letras_numeros, plan_treatment := plan_tratamiento):
            messages.error(request, "❌ Plan de tratamiento inválido: Mínimo 3 caracteres (letras/números), sin caracteres especiales.")
            return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)

        if not re.match(regex_letras_numeros, observaciones_clinicas):
            messages.error(request, "❌ Observaciones médicas inválidas: Mínimo 3 caracteres (letras/números), sin caracteres especiales.")
            return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)

        # 3. Validar Síntomas (Solo letras, mínimo 3 caracteres)
        if not re.match(regex_solo_letras, sintomas):
            messages.error(request, "❌ Síntomas inválidos: Mínimo 3 letras, no se permiten números ni caracteres especiales.")
            return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)

        # 4. Validar Costo Total Cobrado (Entero positivo, no se aceptan negativos ni decimales/double)
        try:
            # Si contiene puntos o comas, rechazamos explícitamente para evitar decimales camuflados
            if '.' in costo_str or ',' in costo_str:
                raise ValueError()
                
            costo_int = int(costo_str)
            if costo_int < 0:
                raise ValueError()
                
            costo = Decimal(costo_int)
        except ValueError:
            messages.error(request, "❌ El costo total cobrado debe ser un número entero positivo (sin decimales ni signos negativos).")
            return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)

        # ---- PROCESO DE TRANSACCIÓN ATÓMICA ----
        try:
            with transaction.atomic():
                # 1. Registrar en Historial Médico
                HistorialMedico.objects.update_or_create(
                    id_cita=cita,
                    defaults={
                        'id_tratamiento': tratamiento,
                        'diagnostico': diagnostico,
                        'sintomas': sintomas,
                        'plan_tratamiento': plan_tratamiento,
                        'observaciones_clinicas': observaciones_clinicas,
                        'costo_aplicado': costo,
                        'completado': True
                    }
                )

                # 2. Lógica de Descuento de Inventario Automático
                insumos_receta = TratamientoProducto.objects.filter(id_tratamiento=tratamiento)
                
                for item in insumos_receta:
                    try:
                        producto = item.id_producto 
                        if not producto:
                            continue
                            
                        cantidad_a_descontar = item.cantidad_requerida
                        stock_anterior = producto.stock_actual
                        producto.stock_actual -= cantidad_a_descontar
                        producto.save()
                        
                        MovimientoInventario.objects.create(
                            id_producto=producto,
                            id_usuario=request.user,
                            tipo_movimiento='SALIDA',
                            cantidad=int(cantidad_a_descontar),
                            stock_anterior=stock_anterior,
                            stock_nuevo=producto.stock_actual,
                            motivo=f"Consumo automático: Cita #{cita.id_cita} ({tratamiento.nombre_tratamiento})",
                            id_cita=cita
                        )
                    except Producto.DoesNotExist:
                        print(f"Advertencia: El producto vinculado al tratamiento {tratamiento} no existe.")
                        continue 

                # 3. Finalizar estado de la cita
                estado_fin = EstadoCita.objects.filter(nombre_estado__iexact='Finalizada').first()
                if estado_fin:
                    cita.id_estado_cita = estado_fin
                    cita.save()

            messages.success(request, "✅ Atención guardada e inventario actualizado con éxito.")
            return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)

        except Exception as e:
            messages.error(request, f"❌ Error crítico al guardar la atención: {e}")
            return redirect('dashboard_medico')
    
    return redirect('dashboard_medico')

# --- MOTOR DE DISPONIBILIDAD (AJAX) ---

def obtener_slots_ajax(request):
    doctor_id = request.GET.get('doctor_id')
    fecha_str = request.GET.get('fecha')  # Formato 'YYYY-MM-DD'
    
    if not doctor_id or not fecha_str:
        return JsonResponse({'slots': []})
        
    try:
        # 1. Definir la jornada laboral base (Ejemplo: 8:00 AM a 5:00 PM)
        # Ajusta estos horarios según las reglas de OdontoClinick
        hora_inicio = datetime.strptime("08:00", "%H:%M").time()
        hora_fin = datetime.strptime("17:00", "%H:%M").time()
        duracion_cita = timedelta(minutes=30) # Citas de 30 minutos

        # Construir la lista base de todos los horarios posibles del día
        fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        slots_posibles = []
        
        actual_dt = datetime.combine(fecha_obj, hora_inicio)
        fin_dt = datetime.combine(fecha_obj, hora_fin)
        
        while actual_dt < fin_dt:
            slots_posibles.append(actual_dt.time().strftime("%H:%M"))
            actual_dt += duracion_cita

        # 2. Obtener las citas que YA TIENE ese doctor en esa fecha
        # Excluimos las citas que estén 'Canceladas' para que esas horas sí se liberen
        citas_ocupadas = Cita.objects.filter(
            id_doctor_id=doctor_id,
            fecha_hora__date=fecha_obj
        ).exclude(
            id_estado_cita__nombre_estado__icontains='Cancelada'
        ).values_list('fecha_hora__time', flat=True)

        # Convertir los horarios ocupados a formato string 'HH:MM' para comparar fácilmente
        horas_ocupadas = [t.strftime("%H:%M") for t in citas_ocupadas]

        # 3. FILTRAR: Dejar solo los slots que NO estén en las horas ocupadas
        # Si es el día de hoy, también filtramos las horas que ya pasaron
        hoy = timezone.now().date()
        ahora_time = timezone.now().time().strftime("%H:%M") if fecha_obj == hoy else "00:00"

        slots_libres = [
            slot for slot in slots_posibles 
            if slot not in horas_ocupadas and slot >= ahora_time
        ]

        return JsonResponse({'slots': slots_libres})

    except Exception as e:
        print(f"[ERROR OBTENER SLOTS]: {e}")
        return JsonResponse({'slots': []}, status=500)
        
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