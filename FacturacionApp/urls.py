from django.urls import path
from . import views

urlpatterns = [
    path('cobrar/<int:id_cita>/', views.registrar_pago_cita, name='registrar_pago_cita'),
    path('historial/', views.historial_pagos, name='historial_pagos'),
    path('factura/ticket/<int:id_cita>/', views.generar_factura_ticket, name='generar_factura_ticket'),
]