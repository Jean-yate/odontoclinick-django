from django.urls import path
from . import views

urlpatterns = [
    path('cobrar/<int:id_cita>/', views.registrar_pago_cita, name='generar_cobro'),
    path('historial/', views.historial_pagos, name='historial_pagos'),
    path('exportar/pdf/', views.exportar_pago_pdf, name='exportar_pdf'),
path('exportar/excel/', views.exportar_pago_excel, name='exportar_excel'),
]