from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Sum, Q
from django.urls import reverse
from openpyxl import Workbook
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from .models import Pago, MetodoPago
from CitaApp.models import Cita


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

            if monto_pago <= 0:
                messages.error(request, "❌ El monto debe ser mayor a cero.")
                return render(request, 'FacturacionApp/generar_cobro.html', {
                    'cita': cita, 'metodos': metodos,
                    'total_abonado': cita.total_abonado,
                    'saldo_pendiente': cita.saldo_pendiente
                })

            if monto_pago > cita.saldo_pendiente:
                messages.warning(request, f"⚠️ El abono excede el saldo restante (${cita.saldo_pendiente}).")
                return render(request, 'FacturacionApp/generar_cobro.html', {
                    'cita': cita, 'metodos': metodos,
                    'total_abonado': cita.total_abonado,
                    'saldo_pendiente': cita.saldo_pendiente
                })

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
                messages.success(request, f"💰 Abono de ${monto_pago} registrado con éxito.")

            url_retorno = reverse('lista_citas')
            return redirect(f"{url_retorno}?imprimir_id={cita.id_cita}")

        except ValueError:
            messages.error(request, "❌ Ingresa un monto numérico válido.")
        except Exception as e:
            messages.error(request, f"❌ Error: {e}")

    return render(request, 'FacturacionApp/generar_cobro.html', {
        'cita': cita,
        'metodos': metodos,
        'total_abonado': cita.total_abonado,
        'saldo_pendiente': cita.saldo_pendiente
    })


@login_required
def generar_factura_ticket(request, id_cita):
    cita = get_object_or_404(Cita, id_cita=id_cita)
    pagos = Pago.objects.filter(id_cita=cita).order_by('fecha_pago')
    total_pagado = pagos.aggregate(total=Sum('monto'))['total'] or 0
    costo_total = cita.costo_final if cita.costo_final else 0
    saldo_restante = costo_total - total_pagado

    return render(request, 'FacturacionApp/factura_pos.html', {
        'cita': cita,
        'pagos': pagos,
        'total_abonado_calculado': total_pagado,
        'saldo_pendiente_calculado': max(0, saldo_restante),
        'hoy': timezone.now(),
    })


@login_required
def historial_pagos(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    metodos = MetodoPago.objects.all()
    pagos = Pago.objects.all().select_related(
        'id_cita__id_paciente__id_usuario',
        'id_metodo_pago'
    ).order_by('-fecha_pago')

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    metodo = request.GET.get('metodo')
    paciente = request.GET.get('paciente')
    monto_min = request.GET.get('monto_min')
    monto_max = request.GET.get('monto_max')

    if fecha_inicio:
        pagos = pagos.filter(fecha_pago__date__gte=fecha_inicio)
    if fecha_fin:
        pagos = pagos.filter(fecha_pago__date__lte=fecha_fin)
    if metodo:
        pagos = pagos.filter(id_metodo_pago__id_metodo_pago=metodo)
    if paciente:
        pagos = pagos.filter(
            Q(id_cita__id_paciente__id_usuario__nombre__icontains=paciente) |
            Q(id_cita__id_paciente__id_usuario__apellidos__icontains=paciente)
        )
    if monto_min:
        pagos = pagos.filter(monto__gte=monto_min)
    if monto_max:
        pagos = pagos.filter(monto__lte=monto_max)

    total_recaudado = pagos.aggregate(Sum('monto'))['monto__sum'] or 0

    if request.GET.get('exportar') == 'excel':
        wb = Workbook()
        ws = wb.active
        ws.title = "Historial Pagos"
        ws.append(['Fecha', 'Paciente', 'Método', 'Referencia', 'Monto', 'Notas'])
        for p in pagos:
            ws.append([
                p.fecha_pago.strftime('%d/%m/%Y %H:%M'),
                str(p.id_cita.id_paciente),
                p.id_metodo_pago.nombre_metodo,
                p.referencia or 'Sin referencia',
                str(p.monto),
                p.notas or '',
            ])
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Historial_Pagos.xlsx"'
        wb.save(response)
        return response

    if request.GET.get('exportar') == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("Historial de Pagos - OdontoClinick", styles['Title']))
        elements.append(Paragraph(f"Total recaudado: ${total_recaudado}", styles['Normal']))
        data = [['Fecha', 'Paciente', 'Método', 'Referencia', 'Monto']]
        for p in pagos:
            data.append([
                p.fecha_pago.strftime('%d/%m/%Y'),
                str(p.id_cita.id_paciente),
                p.id_metodo_pago.nombre_metodo,
                p.referencia or 'Sin ref.',
                f"${p.monto}",
            ])
        t = Table(data, colWidths=[80, 120, 80, 80, 60])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        doc.build(elements)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Historial_Pagos.pdf"'
        response.write(buffer.getvalue())
        buffer.close()
        return response

    return render(request, 'FacturacionApp/historial_pagos.html', {
        'pagos': pagos,
        'metodos': metodos,
        'total_recaudado': total_recaudado,
    })