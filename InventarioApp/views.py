from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, F
from django.http import HttpResponse, JsonResponse
from django.db import models
import openpyxl
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# Importaciones de modelos
from .models import Producto, MovimientoInventario
from TratamientoApp.models import Tratamiento, TratamientoProducto
from .forms import ProductoForm
from CuentasApp.models import Usuario 

# --- PERMISOS ---
def es_auxiliar(user):
    if not user.is_authenticated:
        return False
    # Verifica si es Auxiliar o Superusuario
    return getattr(user, 'id_rol', None) and user.id_rol.nombre_rol == 'Auxiliar de Bodega' or user.is_superuser

# --- DASHBOARD PRINCIPAL ---
@login_required
@user_passes_test(es_auxiliar)
def dashboard_auxiliar(request):
    usuario_actual = request.user
    productos_bajo_stock = Producto.objects.filter(stock_actual__lte=models.F('stock_minimo'), activo=1)
    hoy = timezone.now().date()
    proximo_mes = hoy + timedelta(days=30)
    productos_por_vencer = Producto.objects.filter(fecha_vencimiento__range=[hoy, proximo_mes], activo=1)
    total_productos = Producto.objects.filter(activo=1).count()
    ultimos_movimientos = MovimientoInventario.objects.all().order_by('-fecha_movimiento')[:5]
    context = {
        'usuario_perfil': usuario_actual,
        'bajo_stock': productos_bajo_stock,
        'por_vencer': productos_por_vencer,
        'total_productos': total_productos,
        'ultimos_movimientos': ultimos_movimientos,
    }
    return render(request, 'InventarioApp/dashboard_auxiliar.html', context)

# --- GESTIÓN DE INVENTARIO (PRODUCTOS) ---
@login_required
def lista_inventario(request):
    productos = Producto.objects.all().order_by('nombre_producto')
    return render(request, 'InventarioApp/lista_inventario.html', {'productos': productos})

@login_required
def crear_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f"Producto '{producto.nombre_producto}' creado con éxito.")
            return redirect('lista_inventario')
    else:
        form = ProductoForm()
    return render(request, 'InventarioApp/crear_producto.html', {'form': form})

@login_required
def editar_producto(request, id_producto):
    producto = get_object_or_404(Producto, id_producto=id_producto)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f"¡Producto '{producto.nombre_producto}' actualizado!")
            return redirect('lista_inventario')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'InventarioApp/crear_producto.html', {'form': form, 'editando': True, 'producto': producto})

@login_required
def alternar_estado_producto(request, producto_id):
    if request.method == 'POST':
        try:
            producto = Producto.objects.get(id_producto=producto_id)
            producto.activo = 0 if producto.activo == 1 else 1
            producto.save()
            return JsonResponse({'status': 'ok', 'nuevo_estado': producto.activo})
        except Producto.DoesNotExist:
            return JsonResponse({'status': 'error'}, status=404)
    return JsonResponse({'status': 'error'}, status=400)

# --- CONFIGURACIÓN DE RECETAS (SOLO PARA EL AUXILIAR) ---
@login_required
def lista_tratamientos_auxiliar(request):
    """ Muestra la lista simplificada para configurar insumos por tratamiento """
    tratamientos = Tratamiento.objects.filter(activo=1).order_by('nombre_tratamiento')
    return render(request, 'InventarioApp/lista_insumos_auxiliar.html', {'tratamientos': tratamientos})

@login_required
def gestionar_insumos(request, pk):
    """ Relaciona productos de inventario con tratamientos médicos """
    tratamiento = get_object_or_404(Tratamiento, pk=pk)
    if request.method == 'POST':
        producto_id = request.POST.get('producto')
        cantidad = request.POST.get('cantidad')
        producto = get_object_or_404(Producto, id_producto=producto_id)
        
        TratamientoProducto.objects.update_or_create(
            id_tratamiento=tratamiento,
            id_producto=producto,
            defaults={'cantidad_requerida': cantidad}
        )
        messages.success(request, f"Insumo vinculado a {tratamiento.nombre_tratamiento}")
        return redirect('gestionar_insumos', pk=pk)
    
    insumos = TratamientoProducto.objects.filter(id_tratamiento=tratamiento).select_related('id_producto')
    productos = Producto.objects.filter(activo=1)
    return render(request, 'InventarioApp/gestionar_insumos.html', {
        'tratamiento': tratamiento, 
        'insumos': insumos, 
        'productos': productos
    })

@login_required
def eliminar_insumo(request, pk):
    relacion = get_object_or_404(TratamientoProducto, pk=pk)
    id_trat = relacion.id_tratamiento.pk
    relacion.delete()
    messages.error(request, "Insumo eliminado del tratamiento.")
    return redirect('gestionar_insumos', pk=id_trat)

# --- MOVIMIENTOS (ENTRADAS Y SALIDAS) ---
@login_required
def entrada_stock(request, pk):
    producto_obj = get_object_or_404(Producto, id_producto=pk)
    if request.method == 'POST':
        try:
            usuario_personalizado = Usuario.objects.filter(id_usuario=request.user.id).first()
            cantidad = int(request.POST.get('cantidad', 0))
            if cantidad > 0:
                stock_ant = producto_obj.stock_actual
                producto_obj.stock_actual += cantidad
                producto_obj.save()
                MovimientoInventario.objects.create(
                    producto=producto_obj,
                    tipo_movimiento='ENTRADA',
                    cantidad=cantidad,
                    stock_anterior=stock_ant,
                    stock_nuevo=producto_obj.stock_actual,
                    motivo=request.POST.get('motivo', 'Abastecimiento'),
                    id_usuario=usuario_personalizado 
                )
                messages.success(request, f"Entrada registrada para {producto_obj.nombre_producto}.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect('lista_inventario')

@login_required
def salida_stock(request, pk):
    producto_obj = get_object_or_404(Producto, id_producto=pk)
    if request.method == 'POST':
        try:
            usuario_personalizado = Usuario.objects.filter(id_usuario=request.user.id).first()
            cantidad = int(request.POST.get('cantidad', 0))
            if 0 < cantidad <= producto_obj.stock_actual:
                stock_ant = producto_obj.stock_actual
                producto_obj.stock_actual -= cantidad
                producto_obj.save()
                MovimientoInventario.objects.create(
                    producto=producto_obj,
                    tipo_movimiento='SALIDA',
                    cantidad=cantidad,
                    stock_anterior=stock_ant,
                    stock_nuevo=producto_obj.stock_actual,
                    motivo=request.POST.get('motivo', 'Consumo clínico'),
                    id_usuario=usuario_personalizado 
                )
                messages.warning(request, f"Salida registrada de {producto_obj.nombre_producto}.")
            else:
                messages.error(request, "Cantidad no válida o stock insuficiente.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect('lista_inventario')

# --- MÓDULO INFORMES Y KARDEX ---
@login_required
def informes_avanzados(request):
    productos = Producto.objects.filter(activo=1)
    valor_total = productos.aggregate(total=Sum(F('precio_compra') * F('stock_actual')))['total'] or 0
    primer_dia = timezone.now().replace(day=1, hour=0, minute=0)
    inversion_mes = MovimientoInventario.objects.filter(tipo_movimiento='ENTRADA', fecha_movimiento__gte=primer_dia).aggregate(total=Sum(F('cantidad') * F('producto__precio_compra')))['total'] or 0
    hoy = timezone.now()
    labels, datos = [], []
    for i in range(6, -1, -1):
        fecha = hoy - timedelta(days=i)
        labels.append(fecha.strftime('%d/%m'))
        total = MovimientoInventario.objects.filter(tipo_movimiento='SALIDA', fecha_movimiento__date=fecha.date()).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        datos.append(total)
    context = {
        'valor_total': valor_total,
        'inversion_mes': inversion_mes,
        'labels_grafica': labels,
        'datos_grafica': datos,
        'bajo_stock_count': Producto.objects.filter(stock_actual__lte=F('stock_minimo'), activo=1).count(),
        'insumos_criticos': Producto.objects.filter(stock_actual__lte=F('stock_minimo'), activo=1)
    }
    return render(request, 'InventarioApp/informes.html', context)

@login_required
def historial_kardex(request):
    movimientos = MovimientoInventario.objects.all().order_by('-fecha_movimiento')
    return render(request, 'InventarioApp/kardex.html', {'movimientos': movimientos})

@login_required
def centro_reportes(request):
    return render(request, 'InventarioApp/reportes_descarga.html')

# --- EXPORTACIONES EXCEL ---
@login_required
def exportar_inventario_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte de Inventario"
    ws.append(['Código', 'Producto', 'Stock Actual', 'Mínimo', 'Precio Compra', 'Inversión'])
    for p in Producto.objects.filter(activo=1):
        ws.append([p.codigo_producto, p.nombre_producto, p.stock_actual, p.stock_minimo, p.precio_compra, (p.stock_actual * p.precio_compra)])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Reporte_Inventario.xlsx'
    wb.save(response)
    return response

@login_required
def exportar_kardex_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Historial Kardex"
    ws.append(['Fecha', 'Producto', 'Tipo', 'Cantidad', 'Stock Nuevo', 'Motivo'])
    movimientos = MovimientoInventario.objects.all().select_related('producto').order_by('-fecha_movimiento')
    for m in movimientos:
        ws.append([m.fecha_movimiento.strftime('%d/%m/%Y'), m.producto.nombre_producto if m.producto else "N/A", m.tipo_movimiento, m.cantidad, m.stock_nuevo, m.motivo])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Kardex_OdontoClinick.xlsx'
    wb.save(response)
    return response

# --- EXPORTACIONES PDF ---
@login_required
def exportar_inventario_pdf(request):
    try:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Inventario_OdontoClinick.pdf"'
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("Reporte de Inventario Actual - OdontoClinick", styles['Title']))
        elements.append(Paragraph(f"Fecha: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        data = [['Producto', 'Stock', 'Mínimo', 'P. Compra', 'Subtotal']]
        productos = Producto.objects.filter(activo=1)
        
        for p in productos:
            stock = p.stock_actual if p.stock_actual is not None else 0
            precio = p.precio_compra if p.precio_compra is not None else 0
            subtotal = stock * precio
            
            data.append([
                p.nombre_producto[:30], 
                stock, 
                p.stock_minimo, 
                f"${precio}", 
                f"${subtotal}"
            ])
        t = Table(data, colWidths=[200, 50, 50, 80, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.dodgerblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(t)
        doc.build(elements)
        
        response.write(buffer.getvalue())
        buffer.close()
        return response
    except Exception as e:
        messages.error(request, f"Error al generar el PDF: {e}")
        return redirect('centro_reportes')
    
@login_required
def exportar_kardex_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Kardex_Movimientos.pdf"'
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Historial de Movimientos (Kardex)", styles['Title']))
    data = [['Fecha', 'Producto', 'Tipo', 'Cant.', 'Usuario']]
    movimientos = MovimientoInventario.objects.all().select_related('id_usuario', 'producto').order_by('-fecha_movimiento')[:30]
    
    for m in movimientos:
        fecha = m.fecha_movimiento.strftime('%d/%m/%y')
        prod = m.producto.nombre_producto if m.producto else "N/A"
        if m.id_usuario:
            try:
                user = str(m.id_usuario)
            except:
                user = "ID: " + str(m.id_usuario_id) 
        else:
            user = "Sist./Eliminado"
            
        data.append([fecha, prod, m.tipo_movimiento, m.cantidad, user])
    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(t)
    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response


@login_required
def lista_tratamientos_auxiliar(request):
    tratamientos = Tratamiento.objects.filter(activo=1)
    # El nombre aquí DEBE ser igual al del archivo .html
    return render(request, 'InventarioApp/lista_tratamientos_auxiliar.html', {'tratamientos': tratamientos})