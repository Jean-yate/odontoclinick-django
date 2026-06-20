from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, F, Q
from django.http import HttpResponse, JsonResponse
from django.db import models, transaction
import openpyxl
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from .models import Producto, MovimientoInventario, CategoriaProducto,  LoteCompra, DetalleSalida   
from TratamientoApp.models import Tratamiento, TratamientoProducto
from .forms import ProductoForm, EntradaStockForm, SalidaStockForm
from CuentasApp.models import Usuario
from EmpresaApp.models import Empresa  


def es_auxiliar(user):
    if not user.is_authenticated:
        return False
    return (
        getattr(user, 'id_rol', None)
        and user.id_rol.nombre_rol == 'Auxiliar de Bodega'
    ) or user.is_superuser


def es_admin(user):
    return user.is_authenticated and (
        getattr(user, 'is_admin', False) or user.is_superuser
    )


def es_auxiliar_o_admin(user):
    return es_auxiliar(user) or es_admin(user)


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(es_auxiliar)
def dashboard_auxiliar(request):
    usuario_actual = request.user
    productos_bajo_stock = Producto.objects.filter(
        stock_actual__lte=models.F('stock_minimo'), activo=1
    )
    hoy = timezone.now().date()
    proximo_mes = hoy + timedelta(days=30)
    productos_por_vencer = Producto.objects.filter(
        fecha_vencimiento__range=[hoy, proximo_mes], activo=1
    )
    total_productos = Producto.objects.filter(activo=1).count()
    ultimos_movimientos = MovimientoInventario.objects.all().order_by('-fecha_movimiento')[:5]

    return render(request, 'InventarioApp/dashboard_auxiliar.html', {
        'usuario_perfil': usuario_actual,
        'bajo_stock': productos_bajo_stock,
        'por_vencer': productos_por_vencer,
        'total_productos': total_productos,
        'ultimos_movimientos': ultimos_movimientos,
    })


# ─── Lista de Inventario ──────────────────────────────────────────────────────

@login_required
def lista_inventario(request):
    categorias = CategoriaProducto.objects.all()
    # Todas las empresas para el filtro y los modales
    empresas = Empresa.objects.all().order_by('nombre_empresa')
    productos = Producto.objects.all()\
    .select_related('id_categoria')\
    .prefetch_related(
        'lotes',
        'lotes__id_empresa'
    )\
    .order_by('nombre_producto')
    nombre        = request.GET.get('nombre')
    categoria     = request.GET.get('categoria')
    stock_min     = request.GET.get('stock_min')
    stock_max     = request.GET.get('stock_max')
    estado        = request.GET.get('estado')
    empresa_filtro = request.GET.get('empresa')

    if nombre:
        if nombre.startswith('#'):
            cod_limpio = nombre.replace('#', '').strip()
            productos = productos.filter(codigo_producto__icontains=cod_limpio)
        else:
            productos = productos.filter(
                Q(nombre_producto__icontains=nombre) | Q(codigo_producto__icontains=nombre)
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

    # Req 1.1.4: filtrar por empresa a través de MovimientoInventario ENTRADA
    if empresa_filtro:
        ids = MovimientoInventario.objects.filter(
            tipo_movimiento='ENTRADA',
            empresa_asociada__id_empresa=empresa_filtro
        ).values_list('id_producto_id', flat=True).distinct()
        productos = productos.filter(id_producto__in=ids)

    # ── Excel ────────────────────────────────────────────────────────────────
    if request.GET.get('exportar') == 'excel':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Inventario"
        ws.append(['Código', 'Producto', 'Categoría', 'Stock', 'Mínimo', 'P.Venta', 'Vencimiento', 'Estado'])
        for p in productos:
            ws.append([
                p.codigo_producto or 'S/C', p.nombre_producto,
                p.id_categoria.nombre_categoria, p.stock_actual, p.stock_minimo,
                str(p.precio_venta),
                p.fecha_vencimiento.strftime('%d/%m/%Y') if p.fecha_vencimiento else 'N/A',
                'Activo' if p.activo == 1 else 'Inactivo',
            ])
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Inventario.xlsx"'
        wb.save(response)
        return response

    # ── PDF ──────────────────────────────────────────────────────────────────
    if request.GET.get('exportar') == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("Inventario de Productos - OdontoClinick", styles['Title']))
        elements.append(Paragraph(f"Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        data = [['Producto', 'Categoría', 'Stock', 'Mínimo', 'P.Venta', 'Estado']]
        for p in productos:
            data.append([p.nombre_producto[:25], p.id_categoria.nombre_categoria,
                         str(p.stock_actual), str(p.stock_minimo),
                         f"${p.precio_venta}", 'Activo' if p.activo == 1 else 'Inactivo'])
        t = Table(data, colWidths=[140, 90, 50, 50, 70, 60])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#3f2e23')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 8),
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
        'empresas': empresas,
        'total': productos.count(),
    })


# ─── AJAX: buscar usuario por nombre para el modal de salida ──────────────────

# Agrega esto en InventarioApp/views.py
# (ya está en la versión anterior, solo verifica que el JSON sea correcto)

@login_required
def buscar_usuario_ajax(request):
    """
    GET /inventario/buscar-usuario/?q=texto
    Devuelve JSON con clave 'usuarios' (lista).
    Cada elemento: { id_usuario, nombre, apellidos, nombre_usuario }
    """
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'usuarios': []})

    from CuentasApp.models import Usuario
    from django.db.models import Q

    qs = Usuario.objects.filter(
        Q(nombre__icontains=q) |
        Q(apellidos__icontains=q) |
        Q(nombre_usuario__icontains=q)
    ).select_related('id_rol').values(
        'id_usuario', 'nombre', 'apellidos', 'nombre_usuario'
    )[:10]

    return JsonResponse({'usuarios': list(qs)})

@login_required
def detalle_lotes_producto(request, producto_id):
    # Traemos todos los lotes históricos creados por compras/entradas de este producto
    lotes = LoteCompra.objects.filter(
        id_producto=producto_id
    ).select_related('id_empresa').order_by('fecha_compra') # El más viejo primero

    data = []
    for l in lotes:
        # Evaluamos la empresa proveedora que abasteció este lote
        nombre_empresa = l.id_empresa.nombre_empresa if l.id_empresa else "Ajuste Interno / Sin Proveedor"
        
        data.append({
            "id_lote": l.id_lote,
            "empresa": nombre_empresa, # Aquí garantizamos que muestre el PROVEEDOR de la compra
            "precio_compra": l.precio_compra,
            "inicial": l.cantidad_inicial,
            "disponible": l.cantidad_disponible,
            "consumido": l.cantidad_inicial - l.cantidad_disponible,
            "fecha": l.fecha_compra.strftime("%Y-%m-%d %H:%M"),
        })

    return JsonResponse({"lotes": data})


# ─── CRUD Productos ───────────────────────────────────────────────────────────

@login_required
def crear_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            try:
                producto = form.save(commit=False)
                producto.activo = 1
                producto.save()
                messages.success(request, f"Producto '{producto.nombre_producto}' creado con éxito.")
                return redirect('lista_inventario')
            except Exception as e:
                messages.error(request, f"Error inesperado: {e}")
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
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

# ─── Tratamientos ─────────────────────────────────────────────────────────────

@login_required
def lista_tratamientos_auxiliar(request):
    txt_buscar = request.GET.get('buscar', '').strip()
    tratamientos = Tratamiento.objects.filter(activo=1)
    if txt_buscar:
        tratamientos = tratamientos.filter(nombre_tratamiento__icontains=txt_buscar)
    tratamientos = tratamientos.order_by('nombre_tratamiento')
    return render(request, 'InventarioApp/lista_tratamientos_auxiliar.html', {'tratamientos': tratamientos})


@login_required
def gestionar_insumos(request, pk):
    tratamiento = get_object_or_404(Tratamiento, pk=pk)
    if request.method == 'POST':
        producto_id = request.POST.get('producto')
        cantidad    = request.POST.get('cantidad')
        producto    = get_object_or_404(Producto, id_producto=producto_id)
        TratamientoProducto.objects.update_or_create(
            id_tratamiento=tratamiento,
            id_producto=producto,
            defaults={'cantidad_requerida': cantidad}
        )
        messages.success(request, f"Insumo vinculado a {tratamiento.nombre_tratamiento}")
        return redirect('gestionar_insumos', pk=pk)

    insumos  = TratamientoProducto.objects.filter(id_tratamiento=tratamiento).select_related('id_producto')
    productos = Producto.objects.filter(activo=1)
    return render(request, 'InventarioApp/gestionar_insumos.html', {
        'tratamiento': tratamiento,
        'insumos': insumos,
        'productos': productos,
    })


@login_required
def eliminar_insumo(request, pk):
    relacion = get_object_or_404(TratamientoProducto, pk=pk)
    id_trat  = relacion.id_tratamiento.pk
    relacion.delete()
    messages.error(request, "Insumo eliminado del tratamiento.")
    return redirect('gestionar_insumos', pk=id_trat)


# ─── Movimientos de Bodega ────────────────────────────────────────────────────

@login_required
def entrada_stock(request, pk):
    producto_obj = get_object_or_404(Producto, id_producto=pk)
    if request.method == 'POST':
        form = EntradaStockForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    cantidad = form.cleaned_data['cantidad']
                    motivo   = form.cleaned_data.get('motivo') or 'Entrada de stock'
                    empresa  = form.cleaned_data.get('empresa')
                    precio   = form.cleaned_data.get('precio_transaccion')
 
                    stock_anterior = producto_obj.stock_actual
                    producto_obj.stock_actual += cantidad
                    producto_obj.save()
 
                    # 1. Registrar el movimiento
                    mov = MovimientoInventario.objects.create(
                        id_producto=producto_obj,
                        tipo_movimiento='ENTRADA',
                        cantidad=cantidad,
                        stock_anterior=stock_anterior,
                        stock_nuevo=producto_obj.stock_actual,
                        motivo=motivo,
                        id_usuario=request.user,
                        empresa_asociada=empresa,
                        precio_transaccion=precio,
                    )
 
                    # 2. Crear lote si hay precio de compra (es compra real, no ajuste)
                    if precio is not None:
                        LoteCompra.objects.create(
                            id_producto=producto_obj,
                            id_empresa=empresa,
                            precio_compra=precio,
                            cantidad_inicial=cantidad,
                            cantidad_disponible=cantidad,
                            id_movimiento_entrada=mov,
                        )
 
                    # 3. Actualizar ProductoEmpresa (tabla de relación proveedor)
                    if empresa and precio is not None:
                        from .models import ProductoEmpresa
                        pe, created = ProductoEmpresa.objects.get_or_create(
                            id_producto=producto_obj,
                            id_empresa=empresa,
                            precio_compra_proveedor=precio,
                            defaults={'stock_proveedor': cantidad},
                        )
                        if not created:
                            pe.stock_proveedor += cantidad
                            pe.save()
 
                messages.success(
                    request,
                    f"✓ Entrada de {cantidad} uds. registrada"
                    + (f" — {empresa.nombre_empresa} @ ${precio}/ud." if empresa else ".")
                )
            except Exception as e:
                messages.error(request, f"Error al procesar la entrada: {e}")
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, err)
    return redirect('lista_inventario')

@login_required
def salida_stock(request, pk):  # Usamos 'pk' para solucionar el error TypeError anterior
    if request.method == 'POST':
        producto = get_object_or_404(Producto, id_producto=pk)
        cantidad_a_retirar = int(request.POST.get('cantidad', 0))
        motivo = request.POST.get('motivo', '').strip()
        tipo_destino = request.POST.get('tipo_destino', '')
        
        # ── RECOLECCIÓN DE DESTINATARIOS (CORREGIDO) ──
        empresa_id = request.POST.get('empresa', None)
        cliente_id = request.POST.get('cliente_id', None)
        precio_transaccion = request.POST.get('precio_transaccion', '').strip()
        if precio_transaccion:
            precio_transaccion = int(precio_transaccion)
        else:
            # Si se deja vacío, toma el precio de venta configurado en el producto
            precio_transaccion = int(producto.precio_venta) if producto.precio_venta else 0

        # Buscamos las instancias reales de los modelos si vienen en el POST
        empresa_obj = None
        if tipo_destino == 'empresa' and empresa_id:
            empresa_obj = get_object_or_404(Empresa, id_empresa=empresa_id)

        cliente_obj = None
        if tipo_destino == 'cliente' and cliente_id:
            cliente_obj = get_object_or_404(Usuario, id_usuario=cliente_id)

        if cantidad_a_retirar <= 0:
            messages.error(request, "La cantidad debe ser mayor a 0.")
            return redirect('lista_inventario')

        # Control crítico: Evitar stock negativo global
        if cantidad_a_retirar > producto.stock_actual:
            messages.error(request, f"No puedes retirar {cantidad_a_retirar} unidades. Solo hay {producto.stock_actual} en stock total.")
            return redirect('lista_inventario')

        try:
            with transaction.atomic():
                movimiento = {
                    'id_producto': producto,
                    'id_usuario': request.user,
                    'tipo_movimiento': 'SALIDA',
                    'cantidad': cantidad_a_retirar,
                    'stock_anterior': producto.stock_actual,
                    'stock_nuevo': producto.stock_actual - cantidad_a_retirar,
                    'motivo': motivo,
                    'precio_transaccion': int(precio_transaccion) if precio_transaccion else None
                }

                # Asignación segura de la Empresa Destinataria
                if tipo_destino == 'empresa' and empresa_obj:
                    # Django mapea la columna nativa sumando '_id' a la ForeignKey
                    if hasattr(MovimientoInventario(), 'id_empresa_id'):
                        movimiento['id_empresa'] = empresa_obj
                    elif hasattr(MovimientoInventario(), 'empresa_id'):
                        movimiento['empresa'] = empresa_obj

                # Asignación segura del Cliente / Usuario que recibe
                if tipo_destino == 'cliente' and cliente_obj:
                    if hasattr(MovimientoInventario(), 'id_cliente_id'):
                        movimiento['id_cliente'] = cliente_obj
                    elif hasattr(MovimientoInventario(), 'cliente_id'):
                        movimiento['cliente'] = cliente_obj
                    elif hasattr(MovimientoInventario(), 'id_usuario_recibe_id'): 
                        # Algunos sistemas lo nombran rastreando el ID del usuario receptor
                        movimiento['id_usuario_recibe'] = cliente_obj

                # Creamos el registro pasando el diccionario de parámetros válidos
                movimiento = MovimientoInventario.objects.create(**movimiento)

                # 2. ALGORITMO FIFO: Consumo en cascada lote por lote
                lotes_disponibles = LoteCompra.objects.filter(
                    id_producto=producto,
                    cantidad_disponible__gt=0
                ).order_by('fecha_compra')

                por_descontar = cantidad_a_retirar
                costo_acumulado_salida = 0

                for lote in lotes_disponibles:
                    if por_descontar <= 0:
                        break

                    if lote.cantidad_disponible >= por_descontar:
                        # El lote actual cubre todo lo que queda
                        cantidad_tomada = por_descontar
                        lote.cantidad_disponible -= cantidad_tomada
                        lote.save()

                        DetalleSalida.objects.create(
                            id_movimiento=movimiento,
                            id_lote=lote,
                            cantidad=cantidad_tomada,
                            precio_compra=lote.precio_compra
                        )
                        costo_acumulado_salida += (cantidad_tomada * lote.precio_compra)
                        por_descontar = 0
                    else:
                        # El lote no alcanza por completo, se agota al máximo (llega a 0) y pasa al siguiente lote
                        cantidad_tomada = lote.cantidad_disponible
                        por_descontar -= cantidad_tomada
                        lote.cantidad_disponible = 0
                        lote.save()

                        DetalleSalida.objects.create(
                            id_movimiento=movimiento,
                            id_lote=lote,
                            cantidad=cantidad_tomada,
                            precio_compra=lote.precio_compra
                        )
                        costo_acumulado_salida += (cantidad_tomada * lote.precio_compra)

                if por_descontar > 0:
                    raise Exception("Los lotes no son suficientes para cubrir la salida solicitada.")

                # 3. Guardar costo promedio de salida en el historial del Kardex
                if cantidad_a_retirar > 0:
                    movimiento.costo_unitario_salida = int(costo_acumulado_salida / cantidad_a_retirar)
                    movimiento.save()

                # 4. Actualizar stock en la tabla principal de Productos
                producto.stock_actual -= cantidad_a_retirar
                producto.save()

            messages.success(request, f"Salida de {cantidad_a_retirar} unidades registrada con éxito usando FIFO.")
        except Exception as e:
            messages.error(request, f"Error procesando la salida por lotes: {str(e)}")

        return redirect('lista_inventario')

# ─── Informes ─────────────────────────────────────────────────────────────────

@login_required
def informes_avanzados(request):
    productos = Producto.objects.filter(activo=1)
    valor_total = productos.aggregate(total=Sum(F('precio_venta') * F('stock_actual')))['total'] or 0
    primer_dia  = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inversion_mes = MovimientoInventario.objects.filter(
        tipo_movimiento='ENTRADA', fecha_movimiento__gte=primer_dia
    ).aggregate(total=Sum(F('cantidad') * F('id_producto__precio_venta')))['total'] or 0

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
        'insumos_criticos': Producto.objects.filter(stock_actual__lte=F('stock_minimo'), activo=1),
    })


# ─── Kardex ───────────────────────────────────────────────────────────────────
@login_required
def historial_kardex(request):
    movimientos = MovimientoInventario.objects.all().select_related(
        'id_producto',
        'id_usuario',
        'empresa_asociada',
        'cliente_externo',
        'id_cita',
        'id_cita__id_paciente',
        'id_cita__id_paciente__id_usuario',
    ).order_by('-fecha_movimiento')
 
    producto_id = request.GET.get('producto_id')
    producto_seleccionado = None
    if producto_id:
        producto_seleccionado = get_object_or_404(Producto, id_producto=producto_id)
        movimientos = movimientos.filter(id_producto=producto_seleccionado)
 
    fecha_inicio   = request.GET.get('fecha_inicio')
    fecha_fin      = request.GET.get('fecha_fin')
    tipo           = request.GET.get('tipo')
    usuario_q      = request.GET.get('usuario')
    query          = request.GET.get('producto', '').strip()
    empresa_filtro = request.GET.get('empresa')
 
    if query and not producto_id:
        if query.startswith('#'):
            movimientos = movimientos.filter(
                id_producto__codigo_producto__icontains=query.replace('#', ''))
        else:
            movimientos = movimientos.filter(id_producto__nombre_producto__icontains=query)
    if fecha_inicio:
        movimientos = movimientos.filter(fecha_movimiento__date__gte=fecha_inicio)
    if fecha_fin:
        movimientos = movimientos.filter(fecha_movimiento__date__lte=fecha_fin)
    if tipo:
        movimientos = movimientos.filter(tipo_movimiento=tipo)
    if usuario_q:
        movimientos = movimientos.filter(
            Q(id_usuario__nombre__icontains=usuario_q) |
            Q(id_usuario__apellidos__icontains=usuario_q)
        )
    if empresa_filtro:
        movimientos = movimientos.filter(empresa_asociada__id_empresa=empresa_filtro)
 
    # ── VARIABLES FINANCIERAS INICIALIZADAS CORRECTAMENTE ──
    total_invertido    = 0   # Suma de compras
    total_recaudado    = 0   # Suma de ventas reales
    total_costo_ventas = 0   # Costo real de lo vendido (FIFO)
    total_desperdicio  = 0   # Mermas / pérdidas reales
    total_uso_medico   = 0   # Consumos clínicos legítimos de odontólogos
 
    movimientos_list = list(movimientos)
    for m in movimientos_list:
        cantidad = m.cantidad or 0
        motivo_str = (m.motivo or '').strip().upper()
 
        if m.tipo_movimiento == 'ENTRADA':
            if m.precio_transaccion is not None:
                precio = abs(m.precio_transaccion)
                m.es_referencia = False
            else:
                precio = m.id_producto.precio_venta if m.id_producto else 0
                m.es_referencia = True
            m.total_movimiento = cantidad * (precio or 0)
            total_invertido   += m.total_movimiento
 
        else:  # SALIDA
            if m.precio_transaccion is not None and m.precio_transaccion > 0:
                # Venta real → ingreso monetario
                precio_venta = abs(m.precio_transaccion)
                m.total_movimiento = cantidad * precio_venta
                m.es_referencia    = False
                total_recaudado   += m.total_movimiento
 
                # Costo real FIFO desde el lote
                if m.costo_unitario_salida is not None:
                    m.costo_venta = cantidad * m.costo_unitario_salida
                else:
                    precio_ref = m.id_producto.precio_venta if m.id_producto else 0
                    m.costo_venta = cantidad * (precio_ref or 0)
                total_costo_ventas += m.costo_venta
                m.ganancia_linea = m.total_movimiento - m.costo_venta
            else:
                # Salidas sin precio de cobro directo (Consumos o Pérdidas)
                precio_ref = m.id_producto.precio_venta if m.id_producto else 0
                m.total_movimiento = cantidad * (precio_ref or 0)
                m.es_referencia    = True
                m.costo_venta      = None
                m.ganancia_linea   = None
 
                # Clasificación inteligente basada en el motivo de la salida
                if 'USO MEDICO' in motivo_str or 'TRATAMIENTO' in motivo_str or 'CITA' in motivo_str or m.id_cita:
                    total_uso_medico += m.total_movimiento
                else:
                    total_desperdicio += m.total_movimiento
 
    # DEFINICIÓN DE GANANCIA NETA GLOBAL (CORRIGE EL ERROR DE CONFIGURACIÓN)
    ganancia_neta = total_recaudado - total_costo_ventas
 
    # ── Excel ─────────────────────────────────────────────────────────────────
    if request.GET.get('exportar') == 'excel':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Kardex"
        ws.append([
            'Fecha', 'Producto', 'Tipo', 'Cantidad', 'Stock Ant.', 'Stock Nuevo',
            'Empresa/Cliente', 'Precio/ud.', 'Total', 'Costo ud. (FIFO)',
            'Ganancia línea', 'Motivo', 'Responsable',
        ])
        for m in movimientos_list:
            if m.empresa_asociada:
                destino = m.empresa_asociada.nombre_empresa
            elif m.cliente_externo:
                destino = f"{m.cliente_externo.nombre} {m.cliente_externo.apellidos}"
            elif m.id_cita:
                try:
                    pac = m.id_cita.id_paciente.id_usuario
                    destino = f"{pac.nombre} {pac.apellidos} (Cita #{m.id_cita.id_cita})"
                except Exception:
                    destino = f"Cita #{m.id_cita.id_cita}"
            else:
                destino = '—'
 
            precio_ud = (abs(m.precio_transaccion) if m.precio_transaccion is not None
                         else (m.id_producto.precio_venta if m.id_producto else 0))
            costo_ud  = m.costo_unitario_salida if hasattr(m, 'costo_unitario_salida') and m.costo_unitario_salida else '—'
            gan_lin   = getattr(m, 'ganancia_linea', None)
 
            ws.append([
                m.fecha_movimiento.strftime('%d/%m/%Y %H:%M') if m.fecha_movimiento else 'N/A',
                m.id_producto.nombre_producto if m.id_producto else 'N/A',
                m.tipo_movimiento, m.cantidad, m.stock_anterior, m.stock_nuevo,
                destino,
                f"${precio_ud}" if precio_ud else '—',
                f"${m.total_movimiento}" if m.total_movimiento else '—',
                f"${costo_ud}" if costo_ud != '—' else '—',
                f"${gan_lin}" if gan_lin is not None else '—',
                m.motivo or 'Sin motivo',
                str(m.id_usuario) if m.id_usuario else 'Sistema',
            ])
        ws.append([])
        ws.append(['', '', '', '', '', '', '', '', 'TOTAL INVERTIDO (compras)',   f"${total_invertido}"])
        ws.append(['', '', '', '', '', '', '', '', 'TOTAL RECAUDADO (ventas)',    f"${total_recaudado}"])
        ws.append(['', '', '', '', '', '', '', '', 'COSTO DE VENTAS (FIFO)',      f"${total_costo_ventas}"])
        ws.append(['', '', '', '', '', '', '', '', 'USO CLINICO / MEDICO',        f"${total_uso_medico}"])
        ws.append(['', '', '', '', '', '', '', '', 'DESPERDICIOS / MERMAS',       f"${total_desperdicio}"])
        ws.append(['', '', '', '', '', '', '', '', 'GANANCIA NETA',              f"${ganancia_neta}"])
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Kardex.xlsx"'
        wb.save(response)
        return response
 
    # ── PDF ───────────────────────────────────────────────────────────────────
    if request.GET.get('exportar') == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        titulo = (f"Historial de {producto_seleccionado.nombre_producto}"
                  if producto_seleccionado else "Historial de Movimientos")
        elements.append(Paragraph(titulo, styles['Title']))
        elements.append(Paragraph(
            f"Generado: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        data = [['Fecha', 'Producto', 'Tipo', 'Cant.', 'Stock Nuevo',
                 'Empresa/Cliente', 'Precio', 'Total', 'Ganancia', 'Responsable']]
        for m in movimientos_list:
            if m.empresa_asociada:
                destino = m.empresa_asociada.nombre_empresa[:14]
            elif m.cliente_externo:
                destino = f"{m.cliente_externo.nombre} {m.cliente_externo.apellidos}"[:14]
            elif m.id_cita:
                destino = f"Cita #{m.id_cita.id_cita}"
            else:
                destino = '—'
            precio_ud = (abs(m.precio_transaccion) if m.precio_transaccion is not None
                         else (m.id_producto.precio_venta if m.id_producto else 0))
            gan_lin = getattr(m, 'ganancia_linea', None)
            data.append([
                m.fecha_movimiento.strftime('%d/%m/%y') if m.fecha_movimiento else 'N/A',
                m.id_producto.nombre_producto[:16] if m.id_producto else 'N/A',
                m.tipo_movimiento, str(m.cantidad), str(m.stock_nuevo), destino,
                f"${precio_ud}" if precio_ud else '—',
                f"${m.total_movimiento}" if m.total_movimiento else '—',
                f"${gan_lin}" if gan_lin is not None else '—',
                str(m.id_usuario) if m.id_usuario else 'Sistema',
            ])
        data.append(['', '', '', '', '', '', 'INVERTIDO',  f"${total_invertido}",  '', ''])
        data.append(['', '', '', '', '', '', 'RECAUDADO',  f"${total_recaudado}",  '', ''])
        data.append(['', '', '', '', '', '', 'GANANCIA',   f"${ganancia_neta}",    '', ''])
        t = Table(data, colWidths=[45, 80, 42, 28, 45, 60, 45, 50, 45, 60])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f2e23')),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE',   (0, 0), (-1, -1), 7),
            ('BACKGROUND', (-4, -3), (-1, -1), colors.HexColor('#f0ece9')),
            ('FONTNAME',   (-4, -3), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(t)
        doc.build(elements)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Kardex.pdf"'
        response.write(buffer.getvalue())
        buffer.close()
        return response
 
    empresas_kardex = Empresa.objects.all().order_by('nombre_empresa')
    return render(request, 'InventarioApp/kardex.html', {
        'movimientos':          movimientos_list,
        'total':                len(movimientos_list),
        'producto_seleccionado': producto_seleccionado,
        'empresas':             empresas_kardex,
        'total_invertido':      total_invertido,
        'total_recaudado':      total_recaudado,
        'total_costo_ventas':   total_costo_ventas,
        'total_desperdicio':    total_desperdicio,
        'total_uso_medico':     total_uso_medico,
        'ganancia_neta':        ganancia_neta,
    })