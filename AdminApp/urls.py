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
]