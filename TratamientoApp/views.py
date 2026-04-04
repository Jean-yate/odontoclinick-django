from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from InventarioApp.models import Producto
from .models import Tratamiento, TratamientoProducto
from .forms import TratamientoForm

# --- GESTIÓN CLÍNICA (MÉDICO) ---

@login_required
def lista_tratamiento_medico(request):
    """ Vista con estilo Claymorphism y todos los botones de control """
    tratamientos = Tratamiento.objects.all().order_by('-activo', 'nombre_tratamiento')
    return render(request, 'lista_tratamientos_medico.html', {'tratamientos': tratamientos})

@login_required
def crear_tratamiento(request):
    if request.method == 'POST':
        form = TratamientoForm(request.POST)
        if form.is_valid():
            nuevo_t = form.save(commit=False)
            nuevo_t.activo = 1
            nuevo_t.save()
            messages.success(request, "¡Tratamiento creado con éxito!")
            return redirect('lista_tratamiento_medico')
    else:
        form = TratamientoForm()
    return render(request, 'form_tratamiento.html', {'form': form, 'titulo': 'Nuevo Tratamiento'})

@login_required
def editar_tratamiento(request, pk):
    tratamiento = get_object_or_404(Tratamiento, pk=pk)
    if request.method == 'POST':
        form = TratamientoForm(request.POST, instance=tratamiento)
        if form.is_valid():
            form.save()
            messages.success(request, "Tratamiento actualizado correctamente.")
            return redirect('lista_tratamiento_medico')
    else:
        form = TratamientoForm(instance=tratamiento)
    return render(request, 'form_tratamiento.html', {'form': form, 'titulo': 'Editar Tratamiento'})

@login_required
def toggle_tratamiento(request, pk):
    """ Activar o desactivar un servicio médico """
    if request.method == 'POST': 
        tratamiento = get_object_or_404(Tratamiento, pk=pk)
        tratamiento.activo = 0 if tratamiento.activo == 1 else 1
        tratamiento.save()
        messages.info(request, f"Estado de {tratamiento.nombre_tratamiento} actualizado.")
    return redirect('lista_tratamiento_medico')

# En TratamientoApp/views.py (Asegúrate de que exista esto al final)
@login_required
def ver_insumos_clinicos(request, pk):
    tratamiento = get_object_or_404(Tratamiento, pk=pk)
    insumos = TratamientoProducto.objects.filter(id_tratamiento=tratamiento).select_related('id_producto')
    return render(request, 'ver_insumos.html', {'tratamiento': tratamiento, 'insumos': insumos})

def gestionar_insumos_medico(request, pk):
    # 1. Obtenemos el tratamiento o lanzamos 404 si no existe
    tratamiento = get_object_or_404(Tratamiento, pk=pk)
    
    # 2. Traemos todos los productos activos para el selector
    productos = Producto.objects.filter(activo=1) # Asumiendo que 1 es activo
    
    # 3. Traemos los insumos que ya tiene este tratamiento
    insumos = TratamientoProducto.objects.filter(id_tratamiento=tratamiento)

    # 4. Lógica para GUARDAR un nuevo insumo (POST)
    if request.method == 'POST':
        producto_id = request.POST.get('producto')
        cantidad = request.POST.get('cantidad')
        
        if producto_id and cantidad:
            producto = get_object_or_404(Producto, id_producto=producto_id)
            
            # Creamos o actualizamos el vínculo
            TratamientoProducto.objects.update_or_create(
                id_tratamiento=tratamiento,
                id_producto=producto,
                defaults={'cantidad_requerida': cantidad}
            )
            
            messages.success(request, f"Se ha añadido {producto.nombre_producto} a la receta.")
            return redirect('gestionar_insumos_medico', pk=pk)

    # 5. Renderizamos el nuevo template premium
    return render(request, 'gestionar_insumos_medico.html', {
        'tratamiento': tratamiento,
        'productos': productos,
        'insumos': insumos
    })