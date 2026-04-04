from django import forms
from .models import Tratamiento

class TratamientoForm(forms.ModelForm):
    class Meta:
        model = Tratamiento
        fields = ['codigo', 'nombre_tratamiento', 'descripcion', 'costo_base', 'duracion_estimada_minutos']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control rounded-pill border-0 bg-light px-3', 'placeholder': 'Ej: TRAT-001'}),
            'nombre_treatment': forms.TextInput(attrs={'class': 'form-control rounded-pill border-0 bg-light px-3'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control rounded-4 border-0 bg-light px-3', 'rows': 3}),
            'costo_base': forms.NumberInput(attrs={'class': 'form-control rounded-pill border-0 bg-light px-3'}),
            'duracion_estimada_minutos': forms.NumberInput(attrs={'class': 'form-control rounded-pill border-0 bg-light px-3'}),
        }