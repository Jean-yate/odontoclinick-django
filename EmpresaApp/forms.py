from django import forms
from .models import Empresa
from django.core.exceptions import ValidationError

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nombre_empresa', 'nit', 'es_proveedor', 'es_comprador']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={
                'class': 'form-control input-clay',
                'placeholder': 'Ej: Depósito Dental Central'
            }),
            'nit': forms.TextInput(attrs={
                'class': 'form-control input-clay',
                'placeholder': 'Ej: 900123456-1'
            }),
            'es_proveedor': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_comprador': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_nombre_empresa(self):
        nombre = self.cleaned_data.get('nombre_empresa', '').strip()
        if len(nombre) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres.")
        return nombre

    def clean_nit(self):
        nit = self.cleaned_data.get('nit', '').strip()
        if not nit:
            raise ValidationError("El NIT es obligatorio.")
        return nit
