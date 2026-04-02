from django import forms
from .models import Cita, EstadoCita
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.utils import timezone
from PacienteApp.models import Paciente
from MedicoApp.models import Medico

class AgendarCitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['id_paciente', 'id_doctor', 'fecha_hora', 'id_estado_cita', 'notas_paciente']
        widgets = {
            'fecha_hora': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'notas_paciente': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Motivo de la consulta...'}),
            'id_paciente': forms.Select(attrs={'class': 'form-select'}),
            'id_doctor': forms.Select(attrs={'class': 'form-select'}),
            'id_estado_cita': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # --- SOLUCIÓN AQUÍ ---
        # Filtramos para que solo aparezcan los registros reales de cada tabla
        self.fields['id_paciente'].queryset = Paciente.objects.all()
        self.fields['id_doctor'].queryset = Medico.objects.all()
        
        # Si quieres filtrar solo por médicos ACTIVOS (si tienes ese campo):
        # self.fields['id_doctor'].queryset = Medico.objects.filter(estado='Activo')
        
        self.fields['id_estado_cita'].queryset = EstadoCita.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        doctor = cleaned_data.get('id_doctor')
        fecha_hora_inicio = cleaned_data.get('fecha_hora')

        if fecha_hora_inicio:
            # Validación 1: No fechas pasadas
            if fecha_hora_inicio < timezone.now():
                raise ValidationError("No se pueden agendar citas en fechas o horas pasadas.")

            # Validación 2: Choque de horarios
            if doctor:
                duracion_cita = timedelta(minutes=45) 
                # Buscamos conflictos
                conflictos = Cita.objects.filter(
                    id_doctor=doctor,
                    fecha_hora__lt=fecha_hora_inicio + duracion_cita, 
                    fecha_hora__gt=fecha_hora_inicio - duracion_cita 
                ).exclude(id_estado_cita__nombre_estado='Cancelada')

                if self.instance.pk:
                    conflictos = conflictos.exclude(pk=self.instance.pk)

                if conflictos.exists():
                    raise ValidationError(f"El Dr. {doctor} ya tiene una cita programada cerca de esa hora.")
        
        return cleaned_data