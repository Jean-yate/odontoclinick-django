from django.contrib import admin

from django.contrib import admin
from .models import Cita, EstadoCita

@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('id_cita', 'id_paciente', 'id_doctor', 'fecha_hora', 'id_estado_cita')
    list_filter = ('id_estado_cita', 'fecha_hora')
    date_hierarchy = 'fecha_hora' # Agrega una barra de tiempo arriba
