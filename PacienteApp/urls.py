from django.urls import path
from . import views

urlpatterns = [
    # ... tus otras urls ...
    path('mi-perfil/', views.perfil_paciente, name='perfil_paciente'),
]