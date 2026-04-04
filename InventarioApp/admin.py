from django.contrib import admin
from .models import CategoriaProducto, Producto, MovimientoInventario

@admin.register(CategoriaProducto)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id_categoria', 'nombre_categoria')

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre_producto', 'stock_actual', 'precio_venta', 'activo')
    search_fields = ('nombre_producto',)

@admin.register(MovimientoInventario)
class MovimientoAdmin(admin.ModelAdmin):
    # --- CAMBIO RADICAL AQUÍ ---
    # Quitamos 'id_producto' de la lista principal para que no bloquee el arranque
    list_display = ('id_movimiento', 'mostrar_producto', 'tipo_movimiento', 'cantidad', 'fecha_movimiento')
    
    # Creamos una función "falsa" para mostrar el producto sin que Django se queje
    def mostrar_producto(self, obj):
        return obj.id_producto.nombre_producto
    
    # Le ponemos nombre a la columna en el Admin
    mostrar_producto.short_description = 'Producto'

    list_filter = ('tipo_movimiento', 'fecha_movimiento')