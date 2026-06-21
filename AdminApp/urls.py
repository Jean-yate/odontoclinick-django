from django.urls import path
from . import views

app_name = 'admin_app'

urlpatterns = [
    # Dashboard Principal (Corregida la función de la vista)
    path('', views.dashboard_admin, name='dashboard_admin'),
    
    # CRUD Completo de Usuarios
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/nuevo/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:id_usuario>/editar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:id_usuario>/password/', views.cambiar_password, name='cambiar_password'),
    path('usuarios/<int:id_usuario>/estado/', views.cambiar_estado, name='cambiar_estado'),
    path('roles/', views.lista_roles, name='lista_roles'),
    path('roles/nuevo/', views.crear_rol, name='crear_rol'),
    path('roles/<int:id_rol>/editar/', views.editar_rol, name='editar_rol'),

    # CRUD de catálogos del sistema
    path('estados-cita/', views.lista_estados_cita, name='lista_estados_cita'),
    path('estados-cita/nuevo/', views.crear_estado_cita, name='crear_estado_cita'),
    path('estados-cita/<int:id_estado_cita>/editar/', views.editar_estado_cita, name='editar_estado_cita'),

    path('especialidades/', views.lista_especialidades, name='lista_especialidades'),
    path('especialidades/nuevo/', views.crear_especialidad, name='crear_especialidad'),
    path('especialidades/<int:id_especialidad>/editar/', views.editar_especialidad, name='editar_especialidad'),

    path('estados-usuario/', views.lista_estados_usuario, name='lista_estados_usuario'),
    path('estados-usuario/nuevo/', views.crear_estado_usuario, name='crear_estado_usuario'),
    path('estados-usuario/<int:id_estado>/editar/', views.editar_estado_usuario, name='editar_estado_usuario'),

    path('categorias-producto/', views.lista_categorias_producto, name='lista_categorias_producto'),
    path('categorias-producto/nuevo/', views.crear_categoria_producto, name='crear_categoria_producto'),
    path('categorias-producto/<int:id_categoria>/editar/', views.editar_categoria_producto, name='editar_categoria_producto'),

    path('metodos-pago/', views.lista_metodos_pago, name='lista_metodos_pago'),
    path('metodos-pago/nuevo/', views.crear_metodo_pago, name='crear_metodo_pago'),
    path('metodos-pago/<int:id_metodo_pago>/editar/', views.editar_metodo_pago, name='editar_metodo_pago'),
]