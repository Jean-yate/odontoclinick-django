from django.urls import path
from . import views

urlpatterns = [
    # Dashboard y Listas Base
    path('dashboard/', views.dashboard_auxiliar, name='dashboard_auxiliar'),
    path('productos/', views.lista_inventario, name='lista_inventario'),
    path('historial/', views.historial_kardex, name='kardex'),
    path('informes/', views.informes_avanzados, name='informes'),

    # AJAX
    path('buscar-usuario/', views.buscar_usuario_ajax, name='buscar_usuario_ajax'),
    path('producto/<int:producto_id>/detalle-lotes/', views.detalle_lotes_producto, name='detalle_lotes_producto'),

    # Gestión de Productos
    path('nuevo/', views.crear_producto, name='crear_producto'),
    path('editar/<int:id_producto>/', views.editar_producto, name='editar_producto'),
    path('alternar/<int:producto_id>/', views.alternar_estado_producto, name='alternar_estado_producto'),

    # Movimientos de Bodega
    path('entrada/<int:pk>/', views.entrada_stock, name='entrada_stock'),
    path('salida/<int:pk>/', views.salida_stock, name='salida_stock'),

    # Tratamientos
    path('tratamientos/recetas/', views.lista_tratamientos_auxiliar, name='lista_tratamientos_auxiliar'),
    path('tratamientos/gestionar/<int:pk>/', views.gestionar_insumos, name='gestionar_insumos'),
    path('tratamientos/eliminar-insumo/<int:pk>/', views.eliminar_insumo, name='eliminar_insumo'),
]
