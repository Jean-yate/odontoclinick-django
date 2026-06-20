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
    tratamiento = get_object_or_404(Tratamiento, pk=pk)
    productos = Producto.objects.filter(activo=1) 
    insumos = TratamientoProducto.objects.filter(id_tratamiento=tratamiento)

    if request.method == 'POST':
        producto_id = request.POST.get('producto')
        cantidad = request.POST.get('cantidad')

        try:
            cantidad = int(cantidad)

            if cantidad < 1:
                messages.error(
                    request,
                    'La cantidad debe ser un número entero mayor a cero.'
                )
                return redirect('gestionar_insumos_medico', pk=pk)

        except (TypeError, ValueError):
            messages.error(
                request,
                'Solo se permiten números enteros.'
            )
            return redirect('gestionar_insumos_medico', pk=pk)

        if producto_id:
            producto = get_object_or_404(
                Producto,
                id_producto=producto_id
            )

            TratamientoProducto.objects.update_or_create(
                id_tratamiento=tratamiento,
                id_producto=producto,
                defaults={
                    'cantidad_requerida': cantidad
                }
            )

            messages.success(
                request,
                f"Se ha añadido {producto.nombre_producto} a la receta."
            )

            return redirect(
                'gestionar_insumos_medico',
                pk=pk
            )
    return render(request, 'gestionar_insumos_medico.html', {
        'tratamiento': tratamiento,
        'productos': productos,
        'insumos': insumos
    })

@login_required
def eliminar_inventario_medico(request, pk):
    relacion = get_object_or_404(TratamientoProducto, pk=pk)
    id_trat = (
        relacion.id_tratamiento.pk
        if hasattr(relacion, 'id_tratamiento')
        else relacion.id_treatment.pk
    )
    relacion.delete()
    messages.error(request, "Insumo eliminado del tratamiento.")
    return redirect('gestionar_insumos_medico', pk=id_trat)