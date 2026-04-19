from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, F, Q
from django.http import HttpResponse, JsonResponse
from django.db import models
import openpyxl
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from .models import Producto, MovimientoInventario, CategoriaProducto
from TratamientoApp.models import Tratamiento, TratamientoProducto
from .forms import ProductoForm
from CuentasApp.models import Usuario


def es_auxiliar(user):
    if not user.is_authenticated:
        return False
    return getattr(user, 'id_rol', None) and user.id_rol.nombre_rol == 'Auxiliar de Bodega' or user.is_superuser


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

    return render(request, 'InventarioApp/dashboard_auxiliar.html', {
        'usuario_perfil': usuario_actual,
        'bajo_stock': productos_bajo_stock,
        'por_vencer': productos_por_vencer,
        'total_productos': total_productos,
        'ultimos_movimientos': ultimos_movimientos,
    })


@login_required
def lista_inventario(request):
    from django.db.models import F, Q
    categorias = CategoriaProducto.objects.all()
    productos = Producto.objects.all().select_related('id_categoria').order_by('nombre_producto')

    nombre = request.GET.get('nombre')
    categoria = request.GET.get('categoria')
    stock_min = request.GET.get('stock_min')
    stock_max = request.GET.get('stock_max')
    estado = request.GET.get('estado')
    fecha_vence_inicio = request.GET.get('fecha_vence_inicio')
    fecha_vence_fin = request.GET.get('fecha_vence_fin')

    if nombre:
        if nombre.startswith('#'):
            cod_limpio = nombre.replace('#', '').strip()
            productos = productos.filter(codigo_producto__icontains=cod_limpio)
        else:
            productos = productos.filter(
                Q(nombre_producto__icontains=nombre) |
                Q(codigo_producto__icontains=nombre)
            )
    if categoria:
        productos = productos.filter(id_categoria__id_categoria=categoria)
    if stock_min:
        productos = productos.filter(stock_actual__gte=stock_min)
    if stock_max:
        productos = productos.filter(stock_actual__lte=stock_max)
    if estado == 'activo':
        productos = productos.filter(activo=1)
    if estado == 'inactivo':
        productos = productos.filter(activo=0)
    if estado == 'critico':
        productos = productos.filter(stock_actual__lte=F('stock_minimo'))
    if fecha_vence_inicio:
        productos = productos.filter(fecha_vencimiento__gte=fecha_vence_inicio)
    if fecha_vence_fin:
        productos = productos.filter(fecha_vencimiento__lte=fecha_vence_fin)

    if request.GET.get('exportar') == 'excel':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Inventario"
        ws.append(['Código', 'Producto', 'Categoría', 'Stock', 'Mínimo', 'P.Compra', 'P.Venta', 'Vencimiento', 'Estado'])
        for p in productos:
            ws.append([
                p.codigo_producto or 'S/C',
                p.nombre_producto,
                p.id_categoria.nombre_categoria,
                p.stock_actual,
                p.stock_minimo,
                str(p.precio_compra),
                str(p.precio_venta),
                p.fecha_vencimiento.strftime('%d/%m/%Y') if p.fecha_vencimiento else 'N/A',
                'Activo' if p.activo == 1 else 'Inactivo',
            ])
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Inventario.xlsx"'
        wb.save(response)
        return response

    if request.GET.get('exportar') == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("Inventario de Productos - OdontoClinick", styles['Title']))
        elements.append(Paragraph(f"Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        data = [['Producto', 'Categoría', 'Stock', 'Mínimo', 'P.Venta', 'Estado']]
        for p in productos:
            data.append([
                p.nombre_producto[:25],
                p.id_categoria.nombre_categoria,
                str(p.stock_actual),
                str(p.stock_minimo),
                f"${p.precio_venta}",
                'Activo' if p.activo == 1 else 'Inactivo',
            ])
        t = Table(data, colWidths=[140, 90, 50, 50, 70, 60])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f2e23')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        doc.build(elements)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Inventario.pdf"'
        response.write(buffer.getvalue())
        buffer.close()
        return response

    return render(request, 'InventarioApp/lista_inventario.html', {
        'productos': productos,
        'categorias': categorias,
        'total': productos.count(),
    })


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
    return render(request, 'InventarioApp/crear_producto.html', {
        'form': form, 'editando': True, 'producto': producto
    })


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


@login_required
def lista_tratamientos_auxiliar(request):
    tratamientos = Tratamiento.objects.filter(activo=1).order_by('nombre_tratamiento')
    return render(request, 'InventarioApp/lista_tratamientos_auxiliar.html', {'tratamientos': tratamientos})


@login_required
def gestionar_insumos(request, pk):
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


@login_required
def entrada_stock(request, pk):
    producto_obj = get_object_or_404(Producto, id_producto=pk)
    if request.method == 'POST':
        try:
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
                    id_usuario=request.user
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
                    id_usuario=request.user
                )
                messages.warning(request, f"Salida registrada de {producto_obj.nombre_producto}.")
            else:
                messages.error(request, "Cantidad no válida o stock insuficiente.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect('lista_inventario')


@login_required
def informes_avanzados(request):
    productos = Producto.objects.filter(activo=1)
    valor_total = productos.aggregate(total=Sum(F('precio_compra') * F('stock_actual')))['total'] or 0
    primer_dia = timezone.now().replace(day=1, hour=0, minute=0)
    inversion_mes = MovimientoInventario.objects.filter(
        tipo_movimiento='ENTRADA', fecha_movimiento__gte=primer_dia
    ).aggregate(total=Sum(F('cantidad') * F('producto__precio_compra')))['total'] or 0
    hoy = timezone.now()
    labels, datos = [], []
    for i in range(6, -1, -1):
        fecha = hoy - timedelta(days=i)
        labels.append(fecha.strftime('%d/%m'))
        total = MovimientoInventario.objects.filter(
            tipo_movimiento='SALIDA', fecha_movimiento__date=fecha.date()
        ).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        datos.append(total)

    return render(request, 'InventarioApp/informes.html', {
        'valor_total': valor_total,
        'inversion_mes': inversion_mes,
        'labels_grafica': labels,
        'datos_grafica': datos,
        'bajo_stock_count': Producto.objects.filter(stock_actual__lte=F('stock_minimo'), activo=1).count(),
        'insumos_criticos': Producto.objects.filter(stock_actual__lte=F('stock_minimo'), activo=1)
    })


@login_required
def historial_kardex(request):
    movimientos = MovimientoInventario.objects.all().select_related(
        'producto', 'id_usuario'
    ).order_by('-fecha_movimiento')

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    tipo = request.GET.get('tipo')
    usuario = request.GET.get('usuario')
    query = request.GET.get('producto', '').strip()

    if query:
        if query.startswith('#'):
            cod_limpio = query.replace('#', '')
            movimientos = movimientos.filter(producto__codigo_producto__icontains=cod_limpio)
        else:
            movimientos = movimientos.filter(producto__nombre_producto__icontains=query)
    if fecha_inicio:
        movimientos = movimientos.filter(fecha_movimiento__date__gte=fecha_inicio)
    if fecha_fin:
        movimientos = movimientos.filter(fecha_movimiento__date__lte=fecha_fin)
    if tipo:
        movimientos = movimientos.filter(tipo_movimiento=tipo)
    if usuario:
        movimientos = movimientos.filter(
            Q(id_usuario__nombre__icontains=usuario) |
            Q(id_usuario__apellidos__icontains=usuario)
        )

    if request.GET.get('exportar') == 'excel':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Kardex"
        ws.append(['Fecha', 'Producto', 'Tipo', 'Cantidad', 'Stock Anterior', 'Stock Nuevo', 'Motivo', 'Responsable'])
        for m in movimientos:
            ws.append([
                m.fecha_movimiento.strftime('%d/%m/%Y %H:%M') if m.fecha_movimiento else 'N/A',
                m.producto.nombre_producto if m.producto else 'N/A',
                m.tipo_movimiento,
                m.cantidad,
                m.stock_anterior,
                m.stock_nuevo,
                m.motivo or 'Sin motivo',
                str(m.id_usuario) if m.id_usuario else 'Sistema',
            ])
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Kardex.xlsx"'
        wb.save(response)
        return response

    if request.GET.get('exportar') == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("Historial de Movimientos - OdontoClinick", styles['Title']))
        elements.append(Paragraph(f"Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        data = [['Fecha', 'Producto', 'Tipo', 'Cant.', 'Stock Nuevo', 'Responsable']]
        for m in movimientos:
            data.append([
                m.fecha_movimiento.strftime('%d/%m/%y') if m.fecha_movimiento else 'N/A',
                m.producto.nombre_producto[:20] if m.producto else 'N/A',
                m.tipo_movimiento,
                str(m.cantidad),
                str(m.stock_nuevo),
                str(m.id_usuario) if m.id_usuario else 'Sistema',
            ])
        t = Table(data, colWidths=[70, 120, 70, 40, 60, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f2e23')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        doc.build(elements)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Kardex.pdf"'
        response.write(buffer.getvalue())
        buffer.close()
        return response

    return render(request, 'InventarioApp/kardex.html', {
        'movimientos': movimientos,
        'total': movimientos.count(),
    })