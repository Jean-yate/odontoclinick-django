from django.contrib import admin
import data_wizard
from .models import CategoriaProducto, Producto, MovimientoInventario
from .serializers import ProductoSerializer

@admin.register(CategoriaProducto)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id_categoria', 'nombre_categoria')

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre_producto', 'stock_actual', 'precio_venta', 'activo')
    search_fields = ('nombre_producto',)

@admin.register(MovimientoInventario)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ('id_movimiento', 'mostrar_producto', 'tipo_movimiento', 'cantidad', 'fecha_movimiento')

    def mostrar_producto(self, obj):
        return obj.id_producto.nombre_producto
    mostrar_producto.short_description = 'Producto'

    list_filter = ('tipo_movimiento', 'fecha_movimiento')

data_wizard.register("Productos - Carga Masiva", ProductoSerializer)