from django import forms
from .models import HistorialMedico

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