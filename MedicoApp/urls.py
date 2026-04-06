from django.urls import path
from . import views

urlpatterns = [
    # Dashboard Principal
    path('dashboard/', views.dashboard_medico, name='dashboard_medico'),
    
    # Gestión de Horarios
    path('mis-horarios/', views.mis_horarios, name='mis_horarios'),
    path('mis-horarios/editar/<int:horario_id>/', views.editar_horario, name='editar_horario'),
    path('mis-horarios/eliminar/<int:horario_id>/', views.eliminar_horario, name='eliminar_horario'),
    path('mis-horarios/toggle/<int:horario_id>/', views.toggle_disponibilidad, name='toggle_disponibilidad'),
    
    # Agenda de Citas (Rango de tiempo)
    path('mi-agenda/', views.agenda_semanal, name='ver_citas'),
    path('iniciar-atencion/<int:cita_id>/', views.iniciar_atencion, name='iniciar_atencion'),
    
    # Historial de Tratamientos
    path('historial/', views.historial_tratamientos, name='historial_tratamientos'),
    path('paciente/<int:paciente_id>/', views.perfil_paciente, name='perfil_paciente'),
    path('guardar-atencion/', views.guardar_atencion, name='guardar_atencion'),
    
    # Perfil (Opcional si quieres una vista aparte)
    path('perfil/', views.perfil_medico, name='perfil_medico'),
    path('mi-perfil/editar/', views.editar_perfil_medico, name='editar_perfil_medico'),


]