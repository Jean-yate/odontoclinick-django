# CuentasApp/admin.py
from django.contrib import admin
import data_wizard
from .models import Usuario, Rol, Estado
from .serializers import PacienteMasivoSerializer

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('id_rol', 'nombre_rol', 'descripcion')

@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    list_display = ('id_estado', 'nombre_estado')

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre_usuario', 'nombre', 'apellidos', 'id_rol', 'id_estado')
    list_filter = ('id_rol', 'id_estado')
    search_fields = ('nombre_usuario', 'correo')

data_wizard.register(
    "Pacientes - Carga Masiva",
    PacienteMasivoSerializer
)
