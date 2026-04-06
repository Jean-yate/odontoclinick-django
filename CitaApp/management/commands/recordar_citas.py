from django.core.management.base import BaseCommand
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from CitaApp.models import Cita
from datetime import timedelta

class Command(BaseCommand):
    help = 'Envía recordatorios de citas por correo 24 horas antes'

    def handle(self, *args, **options):
        # 1. Definir el rango de "mañana"
        hoy = timezone.now().date()
        manana = hoy + timedelta(days=1)
        
        # 2. Buscar citas programadas para mañana (excluyendo canceladas si tienes el estado)
        citas_manana = Cita.objects.filter(
            fecha_hora__date=manana
        ).select_related('id_paciente__id_usuario', 'id_doctor__id_usuario')

        sent_count = 0

        for cita in citas_manana:
            paciente = cita.id_paciente.id_usuario
            doctor = cita.id_doctor.id_usuario
            
            context = {
                'paciente': paciente.nombre,
                'fecha': cita.fecha_hora.strftime('%d/%m/%Y'),
                'hora': cita.fecha_hora.strftime('%I:%M %p'),
                'doctor': f"Dr. {doctor.nombre} {doctor.apellidos}"
            }

            html_content = render_to_string('emails/recordatorio_cita.html', context)
            
            email = EmailMessage(
                subject=f"Recordatorio de Cita: {paciente.nombre}, ¡te esperamos mañana!",
                body=html_content,
                from_email='OdontoClinick <tu-correo@gmail.com>',
                to=[paciente.correo],
            )
            email.content_subtype = "html"
            
            try:
                email.send()
                sent_count += 1
                self.stdout.write(self.style.SUCCESS(f'Correo enviado a {paciente.correo}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error enviando a {paciente.correo}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Proceso terminado. Se enviaron {sent_count} recordatorios.'))