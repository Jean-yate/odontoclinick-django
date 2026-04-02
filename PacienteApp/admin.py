from django.contrib import admin

from django.contrib import admin
from .models import Paciente, HistorialMedico

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('id_paciente', 'id_usuario', 'eps', 'rh')
    search_fields = ('id_usuario__nombre', 'eps')

@admin.register(HistorialMedico)
class HistorialAdmin(admin.ModelAdmin):
    list_display = ('id_historial', 'id_paciente', 'id_doctor', 'fecha')
    list_filter = ('fecha',)
