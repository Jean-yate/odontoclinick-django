from django.urls import path
from . import views

urlpatterns = [
    # Dashboard Principal
    path('dashboard/', views.dashboard_medico, name='dashboard_medico'),
    
    # Gestión de Horarios
    path('mis-horarios/', views.mis_horarios, name='mis_horarios'),
    
    # Agenda de Citas (Rango de tiempo)
    path('mi-agenda/', views.agenda_semanal, name='ver_citas'),
    
    # Historial de Tratamientos
    path('historial/', views.historial_tratamientos, name='historial_tratamientos'),
    path('paciente/<int:paciente_id>/', views.perfil_paciente, name='perfil_paciente'),
    path('guardar-atencion/', views.guardar_atencion, name='guardar_atencion'),
    
    # Perfil (Opcional si quieres una vista aparte)
    path('perfil/', views.perfil_medico, name='perfil_medico'),
]