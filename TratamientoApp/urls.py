from django.urls import path
from . import views

urlpatterns = [
    # Cambiamos el nombre de la vista a 'lista_tratamiento_medico'
    path('gestion/', views.lista_tratamiento_medico, name='lista_tratamiento_medico'),
    path('nuevo/', views.crear_tratamiento, name='crear_tratamiento'),
    path('editar/<int:pk>/', views.editar_tratamiento, name='editar_tratamiento'),
    path('toggle/<int:pk>/', views.toggle_tratamiento, name='toggle_tratamiento'),
    path('receta/<int:pk>/', views.gestionar_insumos_medico, name='gestionar_insumos_medico'),
]