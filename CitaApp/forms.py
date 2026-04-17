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
        # Mantenemos los campos que solicitaste
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
        # Filtrado de Querysets
        self.fields['id_paciente'].queryset = Paciente.objects.all()
        self.fields['id_doctor'].queryset = Medico.objects.all()
        self.fields['id_estado_cita'].queryset = EstadoCita.objects.all()

        # Estado inicial por defecto
        if not self.instance.pk:
            estado_inicial = EstadoCita.objects.filter(nombre_estado__icontains='Pendiente').first()
            if estado_inicial:
                self.fields['id_estado_cita'].initial = estado_inicial

    def clean(self):
        """
        Validación personalizada para evitar choques de horario.
        Nota: Como 'fecha_hora' no está en 'fields', este método espera que 
        el objeto ya tenga la fecha asignada o se valide manualmente en la vista.
        """
        cleaned_data = super().clean()
        doctor = cleaned_data.get('id_doctor')
        
        # Intentamos obtener la fecha_hora del objeto si se asignó en la vista antes de validar
        # o si se pasó por el formulario (dependiendo de tu implementación exacta)
        fecha_hora_inicio = getattr(self.instance, 'fecha_hora', None)

        if fecha_hora_inicio and doctor:
            ahora = timezone.now()
            # 1. Evitar fechas pasadas
            if fecha_hora_inicio < ahora:
                raise ValidationError("No se pueden agendar citas en fechas u horas pasadas.")

            # --- NUEVA VALIDACIÓN: Límite Futuro (3 meses / 90 días) ---
            limite_futuro = ahora + timedelta(days=90)
            if fecha_hora_inicio > limite_futuro:
                raise ValidationError("No se permite agendar citas con más de 3 meses de antelación.")

            # 2. Validación de choque de horarios (45 minutos de duración estimada)
            duracion_cita = timedelta(minutes=45)
            
            conflictos = Cita.objects.filter(
                id_doctor=doctor,
                fecha_hora__lt=fecha_hora_inicio + duracion_cita, 
                fecha_hora__gt=fecha_hora_inicio - duracion_cita 
            ).exclude(
                # CLAVE: Excluimos las canceladas para que el horario se considere LIBRE
                id_estado_cita__nombre_estado__icontains='Cancelada'
            )

            # Si estamos editando, excluimos la cita actual de la búsqueda de conflictos
            if self.instance.pk:
                conflictos = conflictos.exclude(pk=self.instance.pk)

            if conflictos.exists():
                raise ValidationError(f"El Dr. {doctor} ya tiene una cita ocupada en este rango de tiempo.")

        return cleaned_data