from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.db.models import Q 
from datetime import datetime
from .models import Cita, EstadoCita 
from .forms import AgendarCitaForm
from FacturacionApp.models import Pago, MetodoPago 
from django.template.loader import render_to_string
from MedicoApp.models import HistorialMedico 
from django.core.mail import EmailMessage

# --- GESTIÓN DE CITAS ---

@login_required
def agendar_cita(request):
    """
    Crea una nueva cita uniendo los campos de fecha y hora 
    que vienen separados desde el frontend dinámico.
    """
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    if request.method == 'POST':
        form = AgendarCitaForm(request.POST)
        fecha_solo = request.POST.get('fecha_seleccionada')
        hora_solo = request.POST.get('hora_seleccionada')

        if not fecha_solo or not hora_solo:
            messages.error(request, "❌ Debes seleccionar una fecha y una hora disponible en el calendario.")
            return render(request, 'CitaApp/agendar_cita.html', {'form': form})

        try:
            # 1. Construir el objeto datetime
            fecha_hora_str = f"{fecha_solo} {hora_solo}"
            fecha_hora_obj = datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M')
            
            # Hacer la fecha "aware" (con zona horaria) si USE_TZ = True en settings
            if timezone.is_aware(timezone.now()):
                fecha_hora_obj = timezone.make_aware(fecha_hora_obj)

            # 2. Asignar la fecha a la instancia del formulario ANTES de validar
            # Esto permite que el método clean() del formulario funcione
            form.instance.fecha_hora = fecha_hora_obj

            if form.is_valid():
                form.save()
                messages.success(request, f'✅ Cita agendada para el {fecha_solo} a las {hora_solo}.')
                return redirect('lista_citas')
            else:
                # Si el formulario no es válido (ej. choque de horario), los errores 
                # aparecerán automáticamente en el template a través de form.errors
                for error in form.non_field_errors():
                    messages.error(request, f"❌ {error}")

        except ValueError:
            messages.error(request, "❌ El formato de fecha u hora es inválido.")
        except Exception as e:
            messages.error(request, f'❌ Error al procesar la cita: {e}')
            
    else:
        form = AgendarCitaForm()
    
    return render(request, 'CitaApp/agendar_cita.html', {
        'form': form,
        'hoy': timezone.now().date()
    })

@login_required
def lista_citas(request):
    busqueda = request.GET.get('buscar')
    citas = Cita.objects.all().select_related(
        'id_paciente__id_usuario', 
        'id_doctor__id_usuario', 
        'id_estado_cita'
    ).order_by('-fecha_hora')

    if busqueda:
        citas = citas.filter(
            Q(id_paciente__id_usuario__nombre__icontains=busqueda) | 
            Q(id_paciente__id_usuario__apellidos__icontains=busqueda) |
            Q(id_doctor__id_usuario__nombre__icontains=busqueda) |
            Q(id_doctor__id_usuario__apellidos__icontains=busqueda) |
            Q(fecha_hora__icontains=busqueda)
        )

    estados_disponibles = EstadoCita.objects.all()

    return render(request, 'CitaApp/lista_citas.html', {
        'citas': citas,
        'estados_disponibles': estados_disponibles,
        'busqueda': busqueda
    })

@login_required
def agenda_diaria(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
    
    hoy = timezone.now().date()
    citas = Cita.objects.filter(fecha_hora__date=hoy).select_related(
        'id_paciente', 'id_doctor', 'id_estado_cita', 'id_paciente__id_usuario'
    ).order_by('fecha_hora')
    
    return render(request, 'CitaApp/agenda_diaria.html', {'citas': citas, 'hoy': hoy})

@login_required
def actualizar_estado_gestion(request, id_cita):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    if request.method == 'POST':
        cita = get_object_or_404(Cita, pk=id_cita)
        nuevo_estado_id = request.POST.get('id_estado')
        nueva_fecha = request.POST.get('nueva_fecha') # Campo del modal

        try:
            with transaction.atomic():
                # 1. Actualizar Estado
                if nuevo_estado_id:
                    estado = get_object_or_404(EstadoCita, pk=nuevo_estado_id)
                    cita.id_estado_cita = estado

                # 2. Actualizar Fecha (si se proporcionó una nueva)
                if nueva_fecha:
                    # Combinamos la nueva fecha con la hora que ya tenía la cita
                    hora_actual = cita.fecha_hora.time()
                    nueva_fecha_obj = datetime.strptime(nueva_fecha, '%Y-%m-%d').date()
                    nueva_fecha_hora = datetime.combine(nueva_fecha_obj, hora_actual)
                    
                    if timezone.is_aware(timezone.now()):
                        nueva_fecha_hora = timezone.make_aware(nueva_fecha_hora)
                    
                    # Validar choque de horario (excluyendo la cita actual)
                    choque = Cita.objects.filter(
                        id_doctor=cita.id_doctor, 
                        fecha_hora=nueva_fecha_hora
                    ).exclude(pk=id_cita).exists()

                    if choque:
                        messages.error(request, f"❌ El Dr. ya tiene una cita a esa hora el {nueva_fecha}.")
                        return redirect('lista_citas')
                    
                    cita.fecha_hora = nueva_fecha_hora

                cita.save()
                messages.success(request, "✅ Gestión de cita actualizada correctamente.")
        
        except Exception as e:
            messages.error(request, f"❌ Error al actualizar: {e}")
        
    return redirect('lista_citas')

@login_required
def cancelar_cita(request, id_cita):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    cita = get_object_or_404(Cita, pk=id_cita)
    estado_cancelado = EstadoCita.objects.filter(nombre_estado__icontains='Cancelada').first()
    
    if estado_cancelado:
        cita.id_estado_cita = estado_cancelado
        cita.save()
        messages.success(request, f"✅ Cita de {cita.id_paciente} cancelada.")
    else:
        messages.error(request, "❌ Error: El estado 'Cancelada' no existe en la base de datos.")
    
    return redirect('lista_citas')

# --- GESTIÓN DE PAGOS Y FACTURACIÓN ---

@login_required
def registrar_pago_cita(request, id_cita):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
        
    cita = get_object_or_404(Cita, pk=id_cita)
    metodos = MetodoPago.objects.filter(activo=1)

    if request.method == 'POST':
        try:
            monto_input = request.POST.get('monto', '0').replace(',', '.')
            monto_pago = float(monto_input)

            if monto_pago > cita.saldo_pendiente:
                messages.warning(request, f"⚠️ El abono (${monto_pago}) excede el saldo (${cita.saldo_pendiente}).")
                return redirect('registrar_pago_cita', id_cita=id_cita)

            if monto_pago <= 0:
                messages.error(request, "❌ El monto debe ser mayor a cero.")
                return redirect('registrar_pago_cita', id_cita=id_cita)

            with transaction.atomic():
                Pago.objects.create(
                    id_cita=cita,
                    fecha_pago=timezone.now(),
                    monto=monto_pago,
                    id_metodo_pago_id=request.POST.get('metodo'),
                    referencia=request.POST.get('referencia'),
                    notas=request.POST.get('notas')
                )
                cita.refresh_from_db()
                messages.success(request, f"💰 Pago de ${monto_pago} guardado. Nuevo saldo: ${cita.saldo_pendiente}")
            
            return redirect('lista_citas')

        except ValueError:
            messages.error(request, "❌ Por favor ingresa un número válido en el monto.")
        except Exception as e:
            messages.error(request, f"❌ Error: {e}")

    context = {
        'cita': cita,
        'metodos': metodos,
        'total_abonado': cita.total_abonado,
        'saldo_pendiente': cita.saldo_pendiente,
        'costo_final': cita.costo_final
    }
    return render(request, 'FacturacionApp/generar_cobro.html', context)

@login_required
def ver_factura_cita(request, id_cita):
    cita = get_object_or_404(Cita, pk=id_cita)
    pagos = Pago.objects.filter(id_cita=cita).order_by('-fecha_pago')
    
    return render(request, 'FacturacionApp/factura_pos.html', {
        'cita': cita,
        'pagos': pagos,
        'hoy': timezone.now(),
    })

@login_required
def enviar_recordatorio_manual(request, cita_id):
    cita = get_object_or_404(Cita, id_cita=cita_id) 
    user_paciente = cita.id_paciente.id_usuario
    user_doctor = cita.id_doctor.id_usuario

    context = {
        'paciente': user_paciente.nombre,
        'fecha': cita.fecha_hora.strftime('%d/%m/%Y'),
        'hora': cita.fecha_hora.strftime('%I:%M %p'),
        'doctor': f"Dr. {user_doctor.nombre} {user_doctor.apellidos}"
    }

    html_content = render_to_string('emails/recordatorio_cita.html', context)
    
    email = EmailMessage(
        subject="Confirmación de tu Cita - OdontoClinick",
        body=html_content,
        from_email='OdontoClinick <tu-correo@gmail.com>',
        to=[user_paciente.correo],
    )
    email.content_subtype = "html"

    try:
        email.send()
        messages.success(request, f"Recordatorio enviado correctamente a {user_paciente.correo}")
    except Exception as e:
        messages.error(request, f"No se pudo enviar el correo: {str(e)}")

    return redirect('lista_citas')


@login_required
def editar_cita_rapido(request, id_cita):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    if request.method == 'POST':
        cita = get_object_or_404(Cita, pk=id_cita)
        
        # Obtener datos del formulario
        fecha_str = request.POST.get('fecha')
        hora_str = request.POST.get('hora')
        nuevo_estado_id = request.POST.get('id_estado')
        motivo = request.POST.get('motivo')

        try:
            # 1. Procesar nueva Fecha y Hora
            if fecha_str and hora_str:
                nueva_fecha_hora = datetime.strptime(f"{fecha_str} {hora_str}", '%Y-%m-%d %H:%M')
                if timezone.is_aware(timezone.now()):
                    nueva_fecha_hora = timezone.make_aware(nueva_fecha_hora)
                
                # Verificar disponibilidad (que no sea el mismo doctor a la misma hora, excluyendo esta cita)
                existe_choque = Cita.objects.filter(
                    id_doctor=cita.id_doctor, 
                    fecha_hora=nueva_fecha_hora
                ).exclude(pk=id_cita).exists()

                if existe_choque:
                    messages.error(request, f"❌ El Dr. ya tiene una cita programada para esa fecha y hora.")
                    return redirect('lista_citas')
                
                cita.fecha_hora = nueva_fecha_hora

            # 2. Actualizar Estado y Motivo
            if nuevo_estado_id:
                cita.id_estado_cita = get_object_or_404(EstadoCita, pk=nuevo_estado_id)
            
            cita.motivo = motivo
            cita.save()
            
            messages.success(request, "✅ Cita actualizada correctamente.")

        except Exception as e:
            messages.error(request, f"❌ Error al actualizar: {e}")
        
    return redirect('lista_citas')