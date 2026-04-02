from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Usuario
from PacienteApp.models import Paciente
from MedicoApp.models import Medico, Especialidad
from django.utils import timezone

@receiver(post_save, sender=Usuario)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        # Si el usuario es un Paciente
        if instance.id_rol.nombre_rol == 'Paciente':
            Paciente.objects.get_or_create(
                id_usuario=instance,
                defaults={'fecha_registro': timezone.now(), 'eps': 'Pendiente'}
            )
        
        # Si el usuario es un Doctor
        elif instance.id_rol.nombre_rol == 'Doctor':
            # Buscamos una especialidad por defecto
            especialidad_gral, _ = Especialidad.objects.get_or_create(nombre_especialidad="General")
            Medico.objects.get_or_create(
                id_usuario=instance,
                defaults={'id_especialidad': especialidad_gral, 'licencia_medica': '000000'}
            )