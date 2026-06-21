from django import forms
from .models import HistorialMedico, Disponibilidad

class RegistroConsultaForm(forms.ModelForm):
    class Meta:
        model = HistorialMedico
        fields = ['id_tratamiento', 'diagnostico', 'observaciones_clinicas', 'costo_aplicado', 'notas_doctor']
        widgets = {
            'diagnostico': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describa el hallazgo...'}),
            'observaciones_clinicas': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'id_tratamiento': forms.Select(attrs={'class': 'form-select'}),
            'costo_aplicado': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class DisponibilidadForm(forms.ModelForm):
    class Meta:
        model = Disponibilidad
        fields = ['dia_semana', 'hora_inicio', 'hora_fin', 'duracion_cita']

    def clean_duracion_cita(self):
        duracion = self.cleaned_data.get("duracion_cita")

        if duracion is None:
            return duracion

        if duracion < 10:
            raise forms.ValidationError("La duración mínima de una cita es 10 minutos.")

        if duracion > 120:
            raise forms.ValidationError("La duración máxima de una cita es 120 minutos.")

        return duracion
    
    def clean(self):
        cleaned_data = super().clean()
    
        inicio = cleaned_data.get("hora_inicio")
        fin = cleaned_data.get("hora_fin")
        duracion = cleaned_data.get("duracion_cita")
    
        if inicio and fin and inicio >= fin:
            raise forms.ValidationError("La hora de inicio debe ser menor que la hora final.")
    
        if duracion:
            if duracion < 10 or duracion > 120:
                raise forms.ValidationError("La duración debe estar entre 10 y 120 minutos.")
    
        return cleaned_data