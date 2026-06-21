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
import re

# Importación de modelos propios y de otras Apps
from .models import Medico, Disponibilidad, HistorialMedico
from CitaApp.models import Cita, EstadoCita
from PacienteApp.models import Paciente
from TratamientoApp.models import Tratamiento, TratamientoProducto
from InventarioApp.models import Producto, MovimientoInventario
from .forms import DisponibilidadForm

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
        form = DisponibilidadForm(request.POST)
        if form.is_valid():
            disponibilidad = form.save(commit=False)
            disponibilidad.id_medico = medico
            disponibilidad.save()
            messages.success(request, "✅ Jornada creada correctamente.")
            return redirect('mis_horarios')
        else:
            messages.error(request, "❌ Revisa los datos del formulario.")
    else:
        form = DisponibilidadForm()
    horarios = Disponibilidad.objects.filter(
        id_medico=medico
    ).order_by('dia_semana', 'hora_inicio')
    return render(request, 'mi_horario.html', {
        'horarios': horarios,
        'form': form
    })

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
    
    paciente = get_object_or_404(
        Paciente.objects.select_related('id_usuario'), 
        id_paciente=paciente_id
    )
    
    # 1. Traemos las citas con sus relaciones optimizadas
    # Nota: Si es OneToOne, cambiamos prefetch_related por select_related para que sea más veloz
    citas = Cita.objects.filter(id_paciente=paciente).select_related(
        'id_doctor__id_usuario', 'id_estado_cita', 'historial'
    ).order_by('-fecha_hora')

    citas_lista = list(citas)

    # 2. Asignamos el historial de forma directa (Sin usar .all())
    for cita in citas_lista:
        try:
            # Al ser OneToOne, Django accede directamente al objeto adjunto
            cita.historial_directo = cita.historial
        except Cita.historial.RelatedObjectDoesNotExist:
            # Si la cita es nueva y no tiene historial aún
            cita.historial_directo = None

    tratamientos = Tratamiento.objects.filter(activo=1)
    
    # 3. Buscamos la cita activa del día
    cita_actual = next(
        (c for c in citas_lista 
         if c.id_doctor.id_usuario == request.user and c.id_estado_cita.nombre_estado in ['Confirmada', 'En Proceso']), 
        None
    )

    return render(request, 'perfil_paciente.html', {
        'paciente': paciente,
        'citas': citas_lista,  
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
    if request.method != 'POST':
        return redirect('dashboard_medico')
 
    id_cita          = request.POST.get('id_cita')
    id_tratamiento_v = request.POST.get('id_tratamiento')
 
    cita       = get_object_or_404(Cita, id_cita=id_cita)
    tratamiento = get_object_or_404(Tratamiento, id_tratamiento=id_tratamiento_v)
 
    # ── Extracción de datos ───────────────────────────────────────────────────
    diagnostico           = request.POST.get('diagnostico', '').strip()
    plan_tratamiento      = request.POST.get('plan_tratamiento', '').strip()
    observaciones_clinicas = request.POST.get('observaciones_clinicas', '').strip()
    sintomas              = request.POST.get('sintomas', '').strip()
    costo_str             = request.POST.get('costo_aplicado', '0').strip()
 
    # ── Validaciones ─────────────────────────────────────────────────────────
    regex_gral   = r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\.,;_\-\?:!\r\n]{3,}$'
    regex_letras = r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s\.,;_\-\?:!\r\n]{3,}$'
 
    if not all([diagnostico, plan_tratamiento, observaciones_clinicas, sintomas, costo_str]):
        messages.error(request, "❌ Todos los campos del registro clínico son obligatorios.")
        return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)
 
    if not re.match(regex_gral, diagnostico):
        messages.error(request, "❌ Diagnóstico inválido (mínimo 3 caracteres).")
        return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)
 
    if not re.match(regex_gral, plan_tratamiento):
        messages.error(request, "❌ Plan de tratamiento inválido (mínimo 3 caracteres).")
        return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)
 
    if not re.match(regex_gral, observaciones_clinicas):
        messages.error(request, "❌ Observaciones inválidas (mínimo 3 caracteres).")
        return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)
 
    if not re.match(regex_letras, sintomas):
        messages.error(request, "❌ Síntomas inválidos: solo letras, mínimo 3 caracteres.")
        return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)
 
    try:
        if '.' in costo_str or ',' in costo_str:
            raise ValueError()
        costo_int = int(costo_str)
        if costo_int < 0:
            raise ValueError()
        costo = Decimal(costo_int)
    except ValueError:
        messages.error(request, "❌ El costo debe ser un número entero positivo.")
        return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)
 
    # ── Transacción atómica ───────────────────────────────────────────────────
    try:
        with transaction.atomic():
 
            # 1. Guardar / actualizar historial médico
            HistorialMedico.objects.update_or_create(
                id_cita=cita,
                defaults={
                    'id_tratamiento':       tratamiento,
                    'diagnostico':          diagnostico,
                    'sintomas':             sintomas,
                    'plan_tratamiento':     plan_tratamiento,
                    'observaciones_clinicas': observaciones_clinicas,
                    'costo_aplicado':       costo,
                    'completado':           True,
                }
            )
 
            # 2. Descontar insumos del inventario
            # BUG FIX 3: int() para evitar conflicto Decimal vs IntegerField
            # Reemplaza todo el bloque "# 2. Descontar insumos del inventario"
            insumos = TratamientoProducto.objects.filter(
                id_tratamiento=tratamiento
            ).select_related('id_producto')
            
            for item in insumos:
                producto = item.id_producto
                if not producto:
                    continue
                
                cantidad = int(item.cantidad_requerida)
                stock_anterior = producto.stock_actual
            
                # Registrar movimiento
                mov = MovimientoInventario.objects.create(
                    id_producto=producto,
                    id_usuario=request.user,
                    tipo_movimiento='SALIDA',
                    cantidad=cantidad,
                    stock_anterior=stock_anterior,
                    stock_nuevo=stock_anterior - cantidad,
                    motivo=f"USO MEDICO - CITA #{cita.id_cita} - {tratamiento.nombre_tratamiento}",
                    id_cita=cita,
                    precio_transaccion=None,
                )
            
                # ── FIFO: descontar lotes igual que salida_stock ──────────────
                from InventarioApp.models import LoteCompra, DetalleSalida
                lotes = LoteCompra.objects.filter(
                    id_producto=producto,
                    cantidad_disponible__gt=0
                ).order_by('fecha_compra')
            
                por_descontar = cantidad
                costo_acumulado = 0
            
                for lote in lotes:
                    if por_descontar <= 0:
                        break
                    if lote.cantidad_disponible >= por_descontar:
                        cantidad_tomada = por_descontar
                        lote.cantidad_disponible -= cantidad_tomada
                        lote.save()
                        DetalleSalida.objects.create(
                            id_movimiento=mov,
                            id_lote=lote,
                            cantidad=cantidad_tomada,
                            precio_compra=lote.precio_compra
                        )
                        costo_acumulado += cantidad_tomada * lote.precio_compra
                        por_descontar = 0
                    else:
                        cantidad_tomada = lote.cantidad_disponible
                        por_descontar -= cantidad_tomada
                        costo_acumulado += cantidad_tomada * lote.precio_compra
                        DetalleSalida.objects.create(
                            id_movimiento=mov,
                            id_lote=lote,
                            cantidad=cantidad_tomada,
                            precio_compra=lote.precio_compra
                        )
                        lote.cantidad_disponible = 0
                        lote.save()
            
                if cantidad > 0:
                    mov.costo_unitario_salida = int(costo_acumulado / cantidad)
                    mov.save()
            
                # Actualizar stock del producto
                producto.stock_actual = stock_anterior - cantidad
                producto.save()
 
            # 3. Finalizar la cita
            estado_fin = EstadoCita.objects.filter(
                nombre_estado__iexact='Finalizada'
            ).first()
            if estado_fin:
                cita.id_estado_cita = estado_fin
                cita.monto_estimado = costo
                cita.save()
 
        messages.success(request, "✅ Atención guardada e inventario actualizado con éxito.")
 
    except Exception as e:
        messages.error(request, f"❌ Error crítico al guardar la atención: {e}")
 
    return redirect('perfil_paciente', paciente_id=cita.id_paciente.id_paciente)
 
 
# ── perfil_paciente corregido ─────────────────────────────────────────────────
# BUG FIX 1: select_related con 'historial' (related_name del OneToOne)
# y asignación explícita de historial_directo para el template
 
@login_required
def perfil_paciente(request, paciente_id):
    """Muestra el expediente del paciente, historial de citas y atención actual."""
    paciente = get_object_or_404(
        Paciente.objects.select_related('id_usuario'),
        id_paciente=paciente_id
    )
 
    # BUG FIX: select_related con 'historial' (el related_name del OneToOne)
    citas = Cita.objects.filter(id_paciente=paciente).select_related(
        'id_doctor__id_usuario',
        'id_estado_cita',
        'historial',                        # ← OneToOne related_name correcto
        'historial__id_tratamiento',        # ← para mostrar nombre del tratamiento
    ).order_by('-fecha_hora')
 
    citas_lista = list(citas)
 
    # Asignar historial_directo a cada cita para el template
    for cita in citas_lista:
        try:
            cita.historial_directo = cita.historial  # acceso OneToOne
        except Exception:
            cita.historial_directo = None
    
        cita.puede_editar = (
        cita.id_doctor.id_usuario == request.user and
        cita.id_estado_cita.nombre_estado != 'Finalizada'
        )
 
    tratamientos = Tratamiento.objects.filter(activo=1)
 
    cita_actual = next(
        (c for c in citas_lista
         if c.id_doctor.id_usuario == request.user
         and c.id_estado_cita.nombre_estado in ['Confirmada', 'En Proceso']),
        None
    )
 
    return render(request, 'perfil_paciente.html', {
        'paciente': paciente,
        'citas': citas_lista,
        'cita_actual': cita_actual,
        'tratamientos': tratamientos,
        'hoy': timezone.now().date(),
    })

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