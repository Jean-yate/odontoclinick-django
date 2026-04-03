from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse

# Librerías para exportar archivos
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from openpyxl import Workbook

# Importación de modelos
from .models import Pago, MetodoPago
from CitaApp.models import Cita

@login_required
def registrar_pago_cita(request, id_cita):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    cita = get_object_or_404(Cita, pk=id_cita)
    metodos = MetodoPago.objects.filter(activo=1)
    pago = Pago.objects.filter(id_cita=cita).first()

    if request.method == 'POST':
        monto = request.POST.get('monto')
        id_metodo = request.POST.get('metodo')
        referencia = request.POST.get('referencia')
        notas = request.POST.get('notas')

        try:
            metodo_instancia = MetodoPago.objects.get(pk=id_metodo)
            
            if pago:
                pago.fecha_pago = timezone.now()
                pago.monto = monto
                pago.id_metodo_pago = metodo_instancia
                pago.referencia = referencia
                pago.notas = notas
                pago.save()
            else:
                Pago.objects.create(
                    id_cita=cita,
                    fecha_pago=timezone.now(),
                    monto=monto,
                    id_metodo_pago=metodo_instancia,
                    referencia=referencia,
                    notas=notas
                )
            
            messages.success(request, f"✅ Pago de ${monto} procesado con éxito para {cita.id_paciente}")
            return redirect('historial_pagos')
            
        except Exception as e:
            messages.error(request, f"❌ Error al procesate el pago: {e}")

    return render(request, 'FacturacionApp/generar_cobro.html', {
        'cita': cita,
        'metodos': metodos,
        'pago': pago 
    })

@login_required
def historial_pagos(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    pagos = Pago.objects.all().order_by('-fecha_pago')
    total_recaudado = sum(pago.monto for pago in pagos)
    
    return render(request, 'FacturacionApp/historial_pagos.html', {
        'pagos': pagos,
        'total_recaudado': total_recaudado
    })

# --- FUNCIONES DE EXPORTACIÓN ---

@login_required
def exportar_pago_pdf(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    pagos = Pago.objects.all().order_by('-fecha_pago')
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Reporte_OdontoClinick.pdf"'
    
    # Crear el lienzo del PDF
    p = canvas.Canvas(response, pagesize=letter)
    p.setTitle("Reporte de Facturación")
    
    # Encabezado
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "ODONTOCLINICK - REPORTE DE FACTURACIÓN")
    p.setFont("Helvetica", 10)
    p.drawString(100, 735, f"Fecha de reporte: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    p.line(100, 730, 550, 730)
    
    # Títulos de columnas
    y = 700
    p.setFont("Helvetica-Bold", 11)
    p.drawString(100, y, "Fecha")
    p.drawString(180, y, "Paciente")
    p.drawString(350, y, "Método")
    p.drawString(480, y, "Monto")
    
    # Listado de pagos
    y -= 20
    p.setFont("Helvetica", 10)
    for pago in pagos:
        p.drawString(100, y, pago.fecha_pago.strftime('%d/%m/%Y'))
        p.drawString(180, y, str(pago.id_cita.id_paciente)[:25])
        p.drawString(350, y, str(pago.id_metodo_pago.nombre_metodo))
        p.drawString(480, y, f"$ {pago.monto}")
        y -= 20
        # Control de fin de página
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
    
    # Encabezados de Excel
    headers = ['Fecha de Pago', 'Paciente', 'Método de Pago', 'Referencia', 'Monto', 'Notas']
    ws.append(headers)
    
    # Llenar datos
    for pago in pagos:
        ws.append([
            pago.fecha_pago.strftime('%d/%m/%Y %H:%M'),
            str(pago.id_cita.id_paciente),
            str(pago.id_metodo_pago.nombre_metodo),
            pago.referencia or "Sin referencia",
            pago.monto,
            pago.notas or ""
        ])
    
    # Preparar la respuesta del navegador
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Reporte_Facturacion.xlsx"'
    wb.save(response)
    
    return response