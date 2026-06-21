from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Case, Value, When, Q, F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

# Modelos y Formularios del Proyecto
from FacturacionApp.models import MetodoPago, Pago
from MedicoApp.models import HistorialMedico
from .forms import AgendarCitaForm
from .models import Cita, EstadoCita
from .utils import enviar_sms_twilio, generar_qr_cita  # CORRECCIÓN: Nombre unificado según utils.py


@login_required
def agendar_cita(request):
    # AJUSTE: Solo el rol operativo (Secretaria) puede agendar la cita directamente
    if request.user.id_rol.nombre_rol != 'Secretaria':
        messages.error(request, "❌ No tienes permisos para agendar citas. Acción exclusiva de Secretaría.")
        return redirect('home')

    paciente_id = request.GET.get('paciente_id')
    
    if request.method == 'POST':
        form = AgendarCitaForm(request.POST)
        fecha_solo = request.POST.get('fecha_seleccionada')
        hora_solo = request.POST.get('hora_seleccionada')

        if not fecha_solo or not hora_solo:
            messages.error(request, "❌ Debes seleccionar una fecha y una hora disponible.")
            return render(request, 'CitaApp/agendar_cita.html', {'form': form})

        try:
            fecha_hora_str = f"{fecha_solo} {hora_solo}"
            fecha_hora_obj = datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M')

            if timezone.is_aware(timezone.now()):
                fecha_hora_obj = timezone.make_aware(fecha_hora_obj)

            form.instance.fecha_hora = fecha_hora_obj

            if form.is_valid():
                with transaction.atomic():
                    cita = form.save()
                    generar_qr_cita(cita)

                try:
                    telefono_paciente = cita.id_paciente.id_usuario.telefono
                    if telefono_paciente:
                        telefono_str = str(telefono_paciente).strip()
                        if not telefono_str.startswith('+') and len(telefono_str) == 10:
                            telefono_str = f"+57{telefono_str}"
                        
                        cita.id_paciente.id_usuario.telefono = telefono_str  
                        sms_enviado = enviar_sms_twilio(cita)
                        
                        if sms_enviado:
                            messages.success(request, f'✅ Cita agendada y notificación SMS enviada para el {fecha_solo}.')
                        else:
                            messages.warning(request, f'✅ Cita agendada, pero falló el despacho del SMS.')
                    else:
                        messages.warning(request, f'✅ Cita agendada, pero el paciente no registra número telefónico.')
                        
                except Exception as api_err:
                    print(f"[ERROR INTEGRACIÓN SMS]: {api_err}")
                    messages.warning(request, f'✅ Cita agendada, pero ocurrió un inconveniente con el proveedor de mensajería.')

                return redirect('lista_citas')
            else:
                for error in form.non_field_errors():
                    messages.error(request, f"❌ {error}")

        except ValueError:
            messages.error(request, "❌ El formato de fecha u hora es inválido.")
        except Exception as e:
            messages.error(request, f'❌ Error al procesar la cita: {e}')
    else:
        initial_data = {'id_paciente': paciente_id} if paciente_id else {}
        form = AgendarCitaForm(initial=initial_data)

    return render(request, 'CitaApp/agendar_cita.html', {
        'form': form,
        'hoy': timezone.now().date(),
        'paciente_preseleccionado': paciente_id
    })


@login_required
def lista_citas(request):
    # AJUSTE: Tanto Secretaria como Administrador pueden VER la lista y generar reportes (Excel/PDF)
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    estados_disponibles = EstadoCita.objects.all()

    citas = Cita.objects.all().select_related(
        'id_paciente__id_usuario',
        'id_doctor__id_usuario',
        'id_estado_cita'
    ).annotate(
        prioridad_estado=Case(
            When(id_estado_cita__nombre_estado__icontains='En Proceso', then=Value(1)),
            When(id_estado_cita__nombre_estado__icontains='En Espera', then=Value(2)),
            When(id_estado_cita__nombre_estado__icontains='Programada', then=Value(3)),
            When(id_estado_cita__nombre_estado__icontains='Finalizada', then=Value(4)),
            When(id_estado_cita__nombre_estado__icontains='Cancelada', then=Value(5)),
            default=Value(6),
        )
    ).order_by('fecha_hora__date', 'prioridad_estado', 'fecha_hora__time')

    # ... [Mantienes intacta toda tu lógica de filtros y exportación Excel/PDF] ...
    busqueda = request.GET.get('buscar')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    doctor = request.GET.get('doctor')
    estado = request.GET.get('estado')
    pago = request.GET.get('pago')
    vista = request.GET.get('vista', 'todas') 

    hoy = timezone.now().date()
    if vista == 'hoy':
        citas = citas.filter(fecha_hora__date=hoy)
    elif vista == 'proximas':
        citas = citas.filter(fecha_hora__date__gt=hoy)
    elif vista == 'historial':
        citas = citas.filter(fecha_hora__date__lt=hoy)

    if busqueda:
        citas = citas.filter(
            Q(id_paciente__id_usuario__nombre__icontains=busqueda) |
            Q(id_paciente__id_usuario__apellidos__icontains=busqueda) |
            Q(id_doctor__id_usuario__nombre__icontains=busqueda) |
            Q(id_doctor__id_usuario__apellidos__icontains=busqueda)
        )
    if fecha_inicio:
        citas = citas.filter(fecha_hora__date__gte=fecha_inicio)
    if fecha_fin:
        citas = citas.filter(fecha_hora__date__lte=fecha_fin)
    if doctor:
        citas = citas.filter(
            Q(id_doctor__id_usuario__nombre__icontains=doctor) |
            Q(id_doctor__id_usuario__apellidos__icontains=doctor)
        )
    if estado:
        citas = citas.filter(id_estado_cita__id_estado_cita=estado)

    if pago == 'pendiente':
        citas = citas.filter(monto_estimado__gt=0, pago__isnull=True)
    elif pago == 'parcial':
        citas = citas.filter(monto_estimado__gt=0, pago__isnull=False).exclude(
            pago__monto__gte=F('monto_estimado')
        )
    elif pago == 'pagado':
        citas = citas.filter(pago__monto__gte=F('monto_estimado'))

    if request.GET.get('exportar') == 'excel':
        wb = Workbook()
        ws = wb.active
        ws.title = "Citas"
        ws.append(['Fecha', 'Paciente', 'Doctor', 'Estado', 'Monto', 'Saldo Pendiente'])
        for c in citas:
            ws.append([
                c.fecha_hora.strftime('%d/%m/%Y %H:%M'),
                f"{c.id_paciente.id_usuario.nombre} {c.id_paciente.id_usuario.apellidos}",
                f"Dr. {c.id_doctor.id_usuario.nombre} {c.id_doctor.id_usuario.apellidos}",
                c.id_estado_cita.nombre_estado if c.id_estado_cita else 'Sin estado',
                str(c.costo_final),
                str(c.saldo_pendiente),
            ])
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Citas.xlsx"'
        wb.save(response)
        return response

    if request.GET.get('exportar') == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("Reporte de Citas - OdontoClinick", styles['Title']))
        elements.append(Paragraph(f"Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        data = [['Fecha', 'Paciente', 'Doctor', 'Estado', 'Monto', 'Saldo']]
        for c in citas:
            data.append([
                c.fecha_hora.strftime('%d/%m/%Y %H:%M'),
                f"{c.id_paciente.id_usuario.nombre} {c.id_paciente.id_usuario.apellidos}",
                f"Dr. {c.id_doctor.id_usuario.nombre}",
                c.id_estado_cita.nombre_estado if c.id_estado_cita else 'Sin estado',
                f"${c.costo_final}",
                f"${c.saldo_pendiente}",
            ])
        t = Table(data, colWidths=[90, 110, 90, 70, 60, 60])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.dodgerblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        doc.build(elements)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Citas.pdf"'
        response.write(buffer.getvalue())
        buffer.close()
        return response

    total_calculado = citas.count()

    return render(request, 'CitaApp/lista_citas.html', {
        'citas': citas,
        'estados_disponibles': estados_disponibles,
        'busqueda': busqueda,
        'total': total_calculado,
    })


@login_required
def agenda_diaria(request):
    # AJUSTE: El tablero diario operativo de la sala de espera queda restringido a Secretaría
    if request.user.id_rol.nombre_rol != 'Secretaria':
        return redirect('home')

    hoy = timezone.now().date()
    citas = Cita.objects.filter(fecha_hora__date=hoy).select_related(
        'id_paciente__id_usuario', 'id_doctor__id_usuario', 'id_estado_cita'
    ).order_by('fecha_hora')

    return render(request, 'CitaApp/agenda_diaria.html', {'citas': citas, 'hoy': hoy})


@login_required
def actualizar_estado_gestion(request, id_cita):
    # AJUSTE: El movimiento de horas o reprogramaciones lo realiza la Secretaría
    if request.user.id_rol.nombre_rol != 'Secretaria':
        return redirect('home')

    if request.method == 'POST':
        cita = get_object_or_404(Cita, pk=id_cita)
        nuevo_estado_id = request.POST.get('id_estado')
        nueva_fecha = request.POST.get('nueva_fecha')
        nueva_hora  = request.POST.get('nueva_hora')   

        try:
            with transaction.atomic():
                if nuevo_estado_id:
                    estado = get_object_or_404(EstadoCita, pk=nuevo_estado_id)
                    cita.id_estado_cita = estado

                if nueva_fecha:
                    if nueva_hora:
                        hora_obj = datetime.strptime(nueva_hora, '%H:%M').time()
                    else:
                        hora_obj = cita.fecha_hora.time()   

                    nueva_fecha_obj  = datetime.strptime(nueva_fecha, '%Y-%m-%d').date()
                    nueva_fecha_hora = datetime.combine(nueva_fecha_obj, hora_obj)

                    if timezone.is_aware(timezone.now()):
                        nueva_fecha_hora = timezone.make_aware(nueva_fecha_hora)

                    choque = Cita.objects.filter(
                        id_doctor=cita.id_doctor,
                        fecha_hora=nueva_fecha_hora
                    ).exclude(pk=id_cita).exclude(
                        id_estado_cita__nombre_estado__icontains='Cancelada'
                    ).exists()

                    if choque:
                        messages.error(request, f"❌ El Dr. ya tiene una cita a esa hora el {nueva_fecha}.")
                        return redirect('lista_citas')

                    cita.fecha_hora = nueva_fecha_hora

                cita.save()
                messages.success(request, "✅ Cita actualizada correctamente.")

        except Exception as e:
            messages.error(request, f"❌ Error al actualizar: {e}")

    return redirect('lista_citas')

@login_required
def cancelar_cita(request, id_cita):
    if request.user.id_rol.nombre_rol != 'Secretaria':
        return redirect('home')

    cita = get_object_or_404(Cita, pk=id_cita)
    estado_cancelado = EstadoCita.objects.filter(nombre_estado__icontains='Cancelada').first()

    if estado_cancelado:
        cita.id_estado_cita = estado_cancelado
        cita.save()
        messages.success(request, f"✅ Cita de {cita.id_paciente} cancelada con éxito.")
    else:
        messages.error(request, "❌ Error: El estado 'Cancelada' no se encuentra configurado.")

    return redirect('lista_citas')


@login_required
def registrar_pago_cita(request, id_cita):
    # AJUSTE: El flujo de caja/recaudo en counter también queda para la Secretaría (o cajero si aplica)
    if request.user.id_rol.nombre_rol != 'Secretaria':
        return redirect('home')

    cita = get_object_or_404(Cita, pk=id_cita)
    metodos = MetodoPago.objects.filter(activo=1)

    if request.method == 'POST':
        try:
            monto_input = request.POST.get('monto', '0').replace(',', '.')
            monto_pago = Decimal(monto_input)

            if monto_pago > cita.saldo_pendiente:
                messages.warning(request, f"⚠️ El abono excede el saldo (${cita.saldo_pendiente}).")
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
                messages.success(request, f"💰 Pago de ${monto_pago} guardado con éxito.")

            return redirect('lista_citas')

        except ValueError:
            messages.error(request, "❌ Por favor ingresa un número válido.")
        except Exception as e:
            messages.error(request, f"❌ Error al procesar el pago: {e}")

    return render(request, 'FacturacionApp/generar_cobro.html', {
        'cita': cita,
        'metodos': metodos,
        'total_abonado': cita.total_abonado,
        'saldo_pendiente': cita.saldo_pendiente,
        'costo_final': cita.costo_final
    })


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

    canal = request.GET.get('canal', 'correo')

    if canal == 'sms':
        try:
            telefono_paciente = user_paciente.telefono
            if telefono_paciente:
                # Limpieza y formateo regional directo
                telefono_str = str(telefono_paciente).strip()
                if not telefono_str.startswith('+') and len(telefono_str) == 10:
                    telefono_str = f"+57{telefono_str}"
                
                user_paciente.telefono = telefono_str  # Sincronización temporal antes del envío
                sms_enviado = enviar_sms_twilio(cita)  # CORRECCIÓN: Llamada a la utilidad HTTP nativa
                
                if sms_enviado:
                    messages.success(request, f'✅ Recordatorio por SMS enviado correctamente a {user_paciente.nombre}.')
                else:
                    messages.error(request, f'❌ El servicio externo no pudo procesar el SMS.')
            else:
                messages.warning(request, f'⚠️ El paciente no cuenta con un número de teléfono registrado.')
        except Exception as e:
            messages.error(request, f'❌ Error al despachar el SMS: {str(e)}')

    elif canal == 'correo':
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
            messages.success(request, f"✅ Recordatorio enviado por Correo a {user_paciente.correo}")
        except Exception as e:
            messages.error(request, f"❌ No se pudo despachar el correo: {str(e)}")
            
    else:
        messages.warning(request, "⚠️ Canal de envío seleccionado no válido.")

    return redirect(request.META.get('HTTP_REFERER', 'lista_citas'))


@login_required
def editar_cita_rapido(request, id_cita):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    if request.method == 'POST':
        cita = get_object_or_404(Cita, pk=id_cita)
        fecha_str = request.POST.get('fecha')
        hora_str = request.POST.get('hora')
        nuevo_estado_id = request.POST.get('id_estado')
        motivo = request.POST.get('motivo')

        try:
            with transaction.atomic():
                if fecha_str and hora_str:
                    nueva_fecha_hora = datetime.strptime(f"{fecha_str} {hora_str}", '%Y-%m-%d %H:%M')
                    if timezone.is_aware(timezone.now()):
                        nueva_fecha_hora = timezone.make_aware(nueva_fecha_hora)

                    existe_choque = Cita.objects.filter(
                        id_doctor=cita.id_doctor,
                        fecha_hora=nueva_fecha_hora
                    ).exclude(pk=id_cita).exists()

                    if existe_choque:
                        messages.error(request, "❌ El Dr. ya tiene una cita reservada para esa fecha y hora.")
                        return redirect('lista_citas')

                    cita.fecha_hora = nueva_fecha_hora

                if nuevo_estado_id:
                    cita.id_estado_cita = get_object_or_404(EstadoCita, pk=nuevo_estado_id)

                cita.motivo = motivo
                cita.save()
                messages.success(request, "✅ Cita modificada de forma rápida correctamente.")

        except Exception as e:
            messages.error(request, f"❌ Error al actualizar la cita: {e}")

    return redirect('lista_citas')


def checkin_qr(request, cita_id):
    cita = get_object_or_404(Cita, pk=cita_id)
    ahora = timezone.now()

    inicio_checkin = cita.fecha_hora - timedelta(minutes=30)
    fin_checkin = cita.fecha_hora + timedelta(hours=2)

    if ahora < inicio_checkin:
        return render(
            request,
            'CitaApp/checkin_no_disponible.html',
            {
                'mensaje': (
                    f'El check-in estará disponible 30 minutos antes de la cita. '
                    f'Su turno es a las {cita.fecha_hora.strftime("%I:%M %p")}.'
                )
            }
        )

    if ahora > fin_checkin:
        return render(
            request,
            'CitaApp/checkin_no_disponible.html',
            {'mensaje': 'El tiempo permitido para realizar el check-in ya expiró.'}
        )

    if cita.hora_llegada:
        return render(
            request,
            'CitaApp/checkin_ya_realizado.html',
            {'cita': cita}
        )

    estado_espera = EstadoCita.objects.filter(nombre_estado__icontains='En Espera').first()
    if not estado_espera:
        return HttpResponse("Error interno: Estado 'En Espera' no configurado.", status=500)

    cita.id_estado_cita = estado_espera
    cita.hora_llegada = ahora
    cita.save()

    return render(request, 'CitaApp/checkin_exitoso.html', {'cita': cita})


def checkin_cita(request, cita_id):
    cita = get_object_or_404(Cita, id_cita=cita_id)

    if not cita.hora_llegada:
        estado_en_proceso = EstadoCita.objects.filter(nombre_estado__icontains='En Proceso').first()
        if estado_en_proceso:
            cita.id_estado_cita = estado_en_proceso

        cita.hora_llegada = timezone.now()
        cita.save()
    return JsonResponse({'status': 'ok'})


@login_required
def pacientes_espera(request):
    estado_espera = EstadoCita.objects.filter(nombre_estado__icontains='En Espera').first()

    citas = Cita.objects.filter(id_estado_cita=estado_espera).select_related(
        'id_paciente__id_usuario',
        'id_doctor__id_usuario'
    ).order_by('hora_llegada')

    return render(request, 'CitaApp/pacientes_espera.html', {'citas': citas})


@login_required
def llamar_paciente(request, cita_id):
    cita = get_object_or_404(Cita, pk=cita_id)

    estado_proceso = EstadoCita.objects.filter(nombre_estado__icontains='En Proceso').first()
    estado_finalizada = EstadoCita.objects.filter(nombre_estado__icontains='Finalizada').first()

    if not estado_proceso or not estado_finalizada:
        messages.error(request, "❌ Error de configuración en los estados de citas.")
        return redirect('lista_citas')

    with transaction.atomic():
        Cita.objects.filter(id_estado_cita=estado_proceso).exclude(pk=cita_id).update(
            id_estado_cita=estado_finalizada
        )

        cita.id_estado_cita = estado_proceso
        cita.hora_llegada = timezone.now()
        cita.save()

    messages.success(request, f"📢 Paciente {cita.id_paciente.id_usuario.nombre} llamado al consultorio.")
    return redirect('panel_secretaria')


def monitor_sala(request):
    pacientes_espera_list = Cita.objects.filter(
        id_estado_cita__nombre_estado__icontains='En Espera'
    ).select_related('id_paciente__id_usuario', 'id_doctor__id_usuario').order_by('hora_llegada')

    paciente_llamado = Cita.objects.filter(
        id_estado_cita__nombre_estado__icontains='En Proceso'
    ).select_related('id_paciente__id_usuario', 'id_doctor__id_usuario').order_by('-hora_llegada').first()

    return render(
        request,
        'CitaApp/monitor_sala.html',
        {
            'pacientes_espera': pacientes_espera_list,
            'paciente_llamado': paciente_llamado
        }
    )

@login_required
def horas_disponibles(request):
    """Devuelve las horas disponibles de un doctor en una fecha dada (JSON)."""
    doctor_id  = request.GET.get('doctor_id')
    fecha_str  = request.GET.get('fecha')
    excluir_id = request.GET.get('excluir_cita')  # cita actual, no cuenta como choque

    if not doctor_id or not fecha_str:
        return JsonResponse({'horas': []})

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'horas': []})

    # Citas ya ocupadas para ese doctor ese día (excluye la cita que se está editando)
    qs = Cita.objects.filter(
        id_doctor_id=doctor_id,
        fecha_hora__date=fecha
    ).exclude(
        id_estado_cita__nombre_estado__icontains='Cancelada'
    )
    if excluir_id:
        qs = qs.exclude(pk=excluir_id)

    horas_ocupadas = set(c.fecha_hora.strftime('%H:%M') for c in qs)

    # Genera bloques de 30 min entre 08:00 y 18:00
    horas_disponibles = []
    inicio = datetime.strptime('08:00', '%H:%M')
    fin    = datetime.strptime('18:00', '%H:%M')
    delta  = timedelta(minutes=30)
    actual = inicio
    while actual <= fin:
        hora_str = actual.strftime('%H:%M')
        if hora_str not in horas_ocupadas:
            horas_disponibles.append(hora_str)
        actual += delta

    return JsonResponse({'horas': horas_disponibles})