from django.contrib import admin
from .models import Paciente  # Quitamos HistorialMedico de aquí

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('id_paciente', 'id_usuario', 'eps', 'rh')
    search_fields = ('id_usuario__nombre', 'eps')
