from datetime import timedelta
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from PacienteApp.models import Paciente
from MedicoApp.models import Medico
from .models import Cita, EstadoCita

class AgendarCitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ['id_paciente', 'id_doctor', 'id_estado_cita', 'monto_estimado']
        
        widgets = {
            'id_paciente': forms.Select(attrs={'class': 'form-select select2'}),
            'id_doctor': forms.Select(attrs={'class': 'form-select', 'id': 'id_doctor'}),
            'id_estado_cita': forms.Select(attrs={'class': 'form-select'}),
            'monto_estimado': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg fw-bold',
                'step': '0.01',
                'placeholder': '0.00'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Optimización con select_related para evitar consultas Queryset duplicadas (Problema N+1)
        self.fields['id_paciente'].queryset = Paciente.objects.filter(
            id_usuario__isnull=False
        ).select_related('id_usuario')
        
        self.fields['id_doctor'].queryset = Medico.objects.filter(
            id_usuario__isnull=False
        ).select_related('id_usuario')
        
        self.fields['id_estado_cita'].queryset = EstadoCita.objects.all()

        # Asignación del estado inicial seguro
        if not self.instance.pk:
            try:
                estado_inicial = EstadoCita.objects.filter(nombre_estado__icontains='Pendiente').first()
                if estado_inicial:
                    self.fields['id_estado_cita'].initial = estado_inicial
            except Exception:
                pass

    def clean(self):
        cleaned_data = super().clean()
        doctor = cleaned_data.get('id_doctor')
        
        # Se obtiene la fecha_hora asignada desde el POST de la vista
        fecha_hora_inicio = getattr(self.instance, 'fecha_hora', None)

        if fecha_hora_inicio and doctor:
            ahora = timezone.now()
            
            # 1. Evitar fechas pasadas
            if fecha_hora_inicio < ahora:
                raise ValidationError("No se pueden agendar citas en fechas u horas pasadas.")

            # 2. Límite Futuro (90 días) - Corregido sin la palabra clave 'let' de JS
            limite_futuro = ahora + timedelta(days=90)
            if fecha_hora_inicio > limite_futuro:
                raise ValidationError("No se permite agendar citas con más de 3 meses de antelación.")

            # 3. Validación de cruce de agendas (excluyendo citas canceladas)
            conflictos = Cita.objects.filter(
                id_doctor=doctor,
                fecha_hora=fecha_hora_inicio
            ).exclude(
                id_estado_cita__nombre_estado__icontains='Cancelada'
            )

            # Si es edición, excluimos la cita actual para evitar un falso positivo
            if self.instance.pk:
                conflictos = conflictos.exclude(pk=self.instance.pk)

            if conflictos.exists():
                raise ValidationError(f"El Dr. {doctor} ya tiene una cita ocupada en este rango de tiempo.")

        return cleaned_data