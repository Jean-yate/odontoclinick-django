# CuentasApp/serializers.py
from rest_framework import serializers
from .models import Usuario, Rol, Estado
from PacienteApp.models import Paciente
from django.utils import timezone

class PacienteMasivoSerializer(serializers.Serializer):
    
    # Campos de Usuario
    nombre_usuario = serializers.CharField(max_length=50)
    password       = serializers.CharField(max_length=255)
    nombre         = serializers.CharField(max_length=50)
    apellidos      = serializers.CharField(max_length=100)
    correo         = serializers.EmailField()
    telefono       = serializers.CharField(max_length=15, required=False)
    
    # Campos de Paciente
    fecha_nacimiento             = serializers.DateField(required=False)
    direccion                    = serializers.CharField(required=False)
    eps                          = serializers.CharField(required=False)
    rh                           = serializers.CharField(required=False)
    alergias                     = serializers.CharField(required=False)
    enfermedades_preexistentes   = serializers.CharField(required=False)
    contacto_emergencia_nombre   = serializers.CharField(required=False)
    contacto_emergencia_telefono = serializers.CharField(required=False)

    def create(self, validated_data):
        rol_paciente  = Rol.objects.get(nombre_rol='Paciente')
        estado_activo = Estado.objects.get(nombre_estado='Activo')
    
        # 1. Crear el Usuario
        usuario = Usuario(
            nombre_usuario = validated_data['nombre_usuario'],
            nombre         = validated_data['nombre'],
            apellidos      = validated_data['apellidos'],
            correo         = validated_data['correo'],
            telefono       = validated_data.get('telefono'),
            id_rol         = rol_paciente,
            id_estado      = estado_activo,
        )
        usuario.set_password(validated_data['password'])
        usuario.save()
        # ↑ Al hacer save(), signals.py ya crea el Paciente automáticamente
    
        # 2. En lugar de crear, actualizamos el Paciente que signals creó
        Paciente.objects.filter(id_usuario=usuario).update(
            fecha_nacimiento             = validated_data.get('fecha_nacimiento'),
            direccion                    = validated_data.get('direccion'),
            eps                          = validated_data.get('eps'),
            rh                           = validated_data.get('rh'),
            alergias                     = validated_data.get('alergias'),
            enfermedades_preexistentes   = validated_data.get('enfermedades_preexistentes'),
            contacto_emergencia_nombre   = validated_data.get('contacto_emergencia_nombre'),
            contacto_emergencia_telefono = validated_data.get('contacto_emergencia_telefono'),
        )
    
        return usuario