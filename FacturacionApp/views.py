from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Sum
from django.urls import reverse

# Librerías para exportar archivos
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from openpyxl import Workbook

# Importación de modelos
from .models import Pago, MetodoPago
from CitaApp.models import Cita

@login_required
def registrar_pago_cita(request, id_cita):
    """
    Registra abonos acumulativos y redirige con orden de impresión automática.
    """
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
        
    cita = get_object_or_404(Cita, pk=id_cita)
    metodos = MetodoPago.objects.filter(activo=1)

    if request.method == 'POST':
        try:
            monto_input = request.POST.get('monto', '0').replace(',', '.')
            monto_pago = float(monto_input)

            # 1. Validación: No dejar cobrar más de lo que debe
            if monto_pago > cita.saldo_pendiente:
                messages.warning(request, f"⚠️ El abono (${monto_pago}) excede el saldo restante (${cita.saldo_pendiente}).")
                return redirect('registrar_pago_cita', id_cita=id_cita)

            # 2. Creación atómica del pago
            with transaction.atomic():
                Pago.objects.create(
                    id_cita=cita,
                    fecha_pago=timezone.now(),
                    monto=monto_pago,
                    id_metodo_pago_id=request.POST.get('metodo'),
                    referencia=request.POST.get('referencia'),
                    notas=request.POST.get('notas')
                )
                
                # Refrescamos la cita para actualizar propiedades
                cita.refresh_from_db()
                
                messages.success(request, f"💰 Abono de ${monto_pago} registrado con éxito.")
            
            # --- CAMBIO CLAVE PARA AUTOMATIZACIÓN ---
            # Redirigimos a la lista de citas pasando el id para que el JS dispare la factura
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
    """
    Genera el ticket POS calculando los valores en tiempo real 
    para evitar conflictos con las @property del modelo Cita.
    """
    cita = get_object_or_404(Cita, id_cita=id_cita)
    
    # 1. Obtenemos el historial de pagos de esta cita específica
    pagos = Pago.objects.filter(id_cita=cita).order_by('fecha_pago')
    
    # 2. Realizamos los cálculos directamente en la vista
    # Nota: Usamos 'costo_final' que ya tienes definido como property en tu modelo
    total_pagado = pagos.aggregate(total=Sum('monto'))['total'] or 0
    saldo_restante = (cita.costo_final or 0) - total_pagado

    # 3. Enviamos los resultados como variables independientes al contexto
    return render(request, 'FacturacionApp/factura_pos.html', {
        'cita': cita,
        'pagos': pagos,
        'total_abonado_calculado': total_pagado,   # Enviamos el dato calculado
        'saldo_pendiente_calculado': saldo_restante, # Enviamos el saldo calculado
        'hoy': timezone.now(),
    })

@login_required
def historial_pagos(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    pagos = Pago.objects.all().order_by('-fecha_pago')
    total_recaudado = pagos.aggregate(Sum('monto'))['monto__sum'] or 0
    
    return render(request, 'FacturacionApp/historial_pagos.html', {
        'pagos': pagos,
        'total_recaudado': total_recaudado
    })

# --- FUNCIONES DE EXPORTACIÓN (REPORTES GENERALES) ---

@login_required
def exportar_pago_pdf(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    pagos = Pago.objects.all().order_by('-fecha_pago')
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Reporte_OdontoClinick.pdf"'
    
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Facturación")
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "ODONTOCLINICK - REPORTE DE FACTURACIÓN")
    p.setFont("Helvetica", 10)
    p.drawString(100, 735, f"Fecha: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    p.line(100, 730, 550, 730)
    
    y = 700
    p.setFont("Helvetica-Bold", 11)
    p.drawString(100, y, "Fecha")
    p.drawString(180, y, "Paciente")
    p.drawString(350, y, "Método")
    p.drawString(480, y, "Monto")
    
    y -= 20
    p.setFont("Helvetica", 10)
    for pago in pagos:
        p.drawString(100, y, pago.fecha_pago.strftime('%d/%m/%Y'))
        p.drawString(180, y, str(pago.id_cita.id_paciente)[:25])
        p.drawString(350, y, str(pago.id_metodo_pago.nombre_metodo))
        p.drawString(480, y, f"$ {pago.monto}")
        y -= 20
        if y < 50:
            p.showPage()
            y = 750
            
    p.showPage()
    p.save()
    return response

@login_required
def exportar_pago_excel(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    pagos = Pago.objects.all().order_by('-fecha_pago')
    wb = Workbook()
    ws = wb.active
    ws.title = "Historial de Pagos"
    
    ws.append(['Fecha de Pago', 'Paciente', 'Método de Pago', 'Referencia', 'Monto', 'Notas'])
    
    for pago in pagos:
        ws.append([
            pago.fecha_pago.strftime('%d/%m/%Y %H:%M'),
            str(pago.id_cita.id_paciente),
            str(pago.id_metodo_pago.nombre_metodo),
            pago.referencia or "Sin referencia",
            pago.monto,
            pago.notas or ""
        ])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Reporte_Facturacion.xlsx"'
    wb.save(response)
    return response