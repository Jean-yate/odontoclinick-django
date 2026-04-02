from django.urls import path
from . import views

urlpatterns = [
    path('agendar/', views.agendar_cita, name='agendar_cita'),
    path('lista/', views.lista_citas, name='lista_citas'),
    path('cancelar/<int:id_cita>/', views.cancelar_cita, name='cancelar_cita'),
]