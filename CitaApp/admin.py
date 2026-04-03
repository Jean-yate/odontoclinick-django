from django.contrib import admin
from .models import Cita, EstadoCita

# 1. Registramos EstadoCita para poder crear "En Proceso", "Finalizada", etc.
@admin.register(EstadoCita)
class EstadoCitaAdmin(admin.ModelAdmin):
    list_display = ('id_estado_cita', 'nombre_estado', 'color')
    search_fields = ('nombre_estado',)

# 2. Tu registro de Cita que ya tenías (está perfecto)
@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('id_cita', 'id_paciente', 'id_doctor', 'fecha_hora', 'id_estado_cita')
    list_filter = ('id_estado_cita', 'id_doctor', 'fecha_hora')
    search_fields = ('id_paciente__id_usuario__nombre', 'id_paciente__id_usuario__apellidos')
    date_hierarchy = 'fecha_hora'