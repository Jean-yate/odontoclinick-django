from django.urls import path
from . import views
from MedicoApp import views as medico_views

urlpatterns = [
    path('agendar/', views.agendar_cita, name='agendar_cita'),
    path('lista/', views.lista_citas, name='lista_citas'),
    path('cancelar/<int:id_cita>/', views.cancelar_cita, name='cancelar_cita'),
    path('actualizar-estado/<int:id_cita>/', views.actualizar_estado_gestion, name='actualizar_estado_gestion'),
    path('ajax/obtener-slots/', medico_views.obtener_slots_ajax, name='obtener_slots_ajax'),
]