from django.contrib import admin
from .models import Medico, Especialidad, Disponibilidad, HistorialMedico

@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    list_display = ('id_especialidad', 'nombre_especialidad')

@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    # CORREGIDO: Usamos id_doctor e id_especialidad que son los nombres en tu models.py
    list_display = ('id_doctor', 'id_usuario', 'id_especialidad', 'licencia_medica')
    search_fields = ('id_usuario__nombre', 'licencia_medica')

@admin.register(Disponibilidad)
class DisponibilidadAdmin(admin.ModelAdmin):
    list_display = ('id_disponibilidad', 'id_medico', 'dia_semana', 'hora_inicio', 'activo')
    list_filter = ('dia_semana', 'activo')

@admin.register(HistorialMedico)
class HistorialAdmin(admin.ModelAdmin):
    # CORREGIDO: Usamos los campos reales de tu nueva tabla
    list_display = ('id_historial', 'id_cita', 'id_tratamiento', 'fecha_creacion')
    list_filter = ('fecha_creacion',)