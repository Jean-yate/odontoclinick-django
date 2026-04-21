from django import forms
from .models import Cita, EstadoCita
from PacienteApp.models import Paciente
from MedicoApp.models import Medico
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.utils import timezone

class AgendarCitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        # Campos solicitados
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
        
        # CORRECCIÓN CLAVE: Usamos select_related para traer al Usuario y evitar el DoesNotExist.
        # Además, filtramos para que solo aparezcan los que realmente tienen un usuario vinculado.
        self.fields['id_paciente'].queryset = Paciente.objects.filter(
            id_usuario__isnull=False
        ).select_related('id_usuario')
        
        self.fields['id_doctor'].queryset = Medico.objects.filter(
            id_usuario__isnull=False
        ).select_related('id_usuario')
        
        self.fields['id_estado_cita'].queryset = EstadoCita.objects.all()

        # Estado inicial por defecto de forma segura
        if not self.instance.pk:
            try:
                estado_inicial = EstadoCita.objects.filter(nombre_estado__icontains='Pendiente').first()
                if estado_inicial:
                    self.fields['id_estado_cita'].initial = estado_inicial
            except Exception:
                pass

    def clean(self):
        """
        Validación personalizada para evitar choques de horario.
        """
        cleaned_data = super().clean()
        doctor = cleaned_data.get('id_doctor')
        
        # Obtenemos la fecha_hora asignada en la vista
        fecha_hora_inicio = getattr(self.instance, 'fecha_hora', None)

        if fecha_hora_inicio and doctor:
            ahora = timezone.now()
            
            # 1. Evitar fechas pasadas
            if fecha_hora_inicio < ahora:
                raise ValidationError("No se pueden agendar citas en fechas u horas pasadas.")

            # 2. Límite Futuro (90 días)
            limite_futuro = ahora + timedelta(days=90)
            if fecha_hora_inicio > limite_futuro:
                raise ValidationError("No se permite agendar citas con más de 3 meses de antelación.")

            # 3. Validación de choque de horarios (45 minutos)
            duracion_cita = timedelta(minutes=45)
            
            conflictos = Cita.objects.filter(
                id_doctor=doctor,
                fecha_hora__lt=fecha_hora_inicio + duracion_cita, 
                fecha_hora__gt=fecha_hora_inicio - duracion_cita 
            ).exclude(
                id_estado_cita__nombre_estado__icontains='Cancelada'
            )

            if self.instance.pk:
                conflictos = conflictos.exclude(pk=self.instance.pk)

            if conflictos.exists():
                raise ValidationError(f"El Dr. {doctor} ya tiene una cita ocupada en este rango de tiempo.")

        return cleaned_data