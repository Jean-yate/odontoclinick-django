from django.urls import path
from . import views

app_name = 'EmpresaApp' 

urlpatterns = [
    path('', views.lista_empresas, name='lista_empresas'),
    path('crear/', views.crear_empresa, name='crear_empresa'),
    path('editar/<int:pk>/', views.editar_empresa, name='editar_empresa'),
    path('alternar-tipo/<int:pk>/', views.alternar_tipo_empresa, name='alternar_tipo_empresa'),
]