from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
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
from openpyxl import Workbook
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


@login_required
def agendar_cita(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

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
                form.save()
                messages.success(request, f'✅ Cita agendada para el {fecha_solo} a las {hora_solo}.')
                return redirect('lista_citas')
            else:
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
    estados_disponibles = EstadoCita.objects.all()

    citas = Cita.objects.all().select_related(
        'id_paciente__id_usuario',
        'id_doctor__id_usuario',
        'id_estado_cita'
    ).order_by('-fecha_hora')

    busqueda = request.GET.get('buscar')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    doctor = request.GET.get('doctor')
    estado = request.GET.get('estado')
    pago = request.GET.get('pago')

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

    # Filtro de pago — se evalúa en Python por ser propiedad calculada
    if pago == 'pendiente':
        citas = [c for c in citas if c.total_abonado == 0 and c.costo_final > 0]
    elif pago == 'parcial':
        citas = [c for c in citas if 0 < c.total_abonado < c.costo_final]
    elif pago == 'pagado':
        citas = [c for c in citas if c.total_abonado >= c.costo_final and c.costo_final > 0]

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
                c.fecha_hora.strftime('%d/%m/%Y'),
                f"{c.id_paciente.id_usuario.nombre} {c.id_paciente.id_usuario.apellidos}",
                f"Dr. {c.id_doctor.id_usuario.nombre}",
                c.id_estado_cita.nombre_estado if c.id_estado_cita else 'Sin estado',
                f"${c.costo_final}",
                f"${c.saldo_pendiente}",
            ])
        t = Table(data, colWidths=[80, 100, 80, 70, 60, 60])
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

    return render(request, 'CitaApp/lista_citas.html', {
        'citas': citas,
        'estados_disponibles': estados_disponibles,
        'busqueda': busqueda,
        'total': len(citas) if isinstance(citas, list) else citas.count(),
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
        nueva_fecha = request.POST.get('nueva_fecha')

        try:
            with transaction.atomic():
                if nuevo_estado_id:
                    estado = get_object_or_404(EstadoCita, pk=nuevo_estado_id)
                    cita.id_estado_cita = estado

                if nueva_fecha:
                    hora_actual = cita.fecha_hora.time()
                    nueva_fecha_obj = datetime.strptime(nueva_fecha, '%Y-%m-%d').date()
                    nueva_fecha_hora = datetime.combine(nueva_fecha_obj, hora_actual)

                    if timezone.is_aware(timezone.now()):
                        nueva_fecha_hora = timezone.make_aware(nueva_fecha_hora)

                    choque = Cita.objects.filter(
                        id_doctor=cita.id_doctor,
                        fecha_hora=nueva_fecha_hora
                    ).exclude(pk=id_cita).exists()

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
                messages.success(request, f"💰 Pago de ${monto_pago} guardado.")

            return redirect('lista_citas')

        except ValueError:
            messages.error(request, "❌ Por favor ingresa un número válido.")
        except Exception as e:
            messages.error(request, f"❌ Error: {e}")

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
        messages.success(request, f"Recordatorio enviado a {user_paciente.correo}")
    except Exception as e:
        messages.error(request, f"No se pudo enviar el correo: {str(e)}")

    return redirect('lista_citas')


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
            if fecha_str and hora_str:
                nueva_fecha_hora = datetime.strptime(f"{fecha_str} {hora_str}", '%Y-%m-%d %H:%M')
                if timezone.is_aware(timezone.now()):
                    nueva_fecha_hora = timezone.make_aware(nueva_fecha_hora)

                existe_choque = Cita.objects.filter(
                    id_doctor=cita.id_doctor,
                    fecha_hora=nueva_fecha_hora
                ).exclude(pk=id_cita).exists()

                if existe_choque:
                    messages.error(request, "❌ El Dr. ya tiene una cita para esa fecha y hora.")
                    return redirect('lista_citas')

                cita.fecha_hora = nueva_fecha_hora

            if nuevo_estado_id:
                cita.id_estado_cita = get_object_or_404(EstadoCita, pk=nuevo_estado_id)

            cita.motivo = motivo
            cita.save()
            messages.success(request, "✅ Cita actualizada correctamente.")

        except Exception as e:
            messages.error(request, f"❌ Error al actualizar: {e}")

    return redirect('lista_citas')