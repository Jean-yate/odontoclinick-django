import re
from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import Tratamiento

class TratamientoForm(forms.ModelForm):
    
    # 1. Validación de Código: [Letras mín 3][-][Números] (Ej: ABC-123 o TRAT-001)
    # Explicación regex: ^[a-zA-Z]{3,} (Mínimo 3 letras) + - (Guion) + \d+ (Uno o más números) $
    codigo = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z]{3,}-\d+$',
                message='El código debe tener al menos 3 letras, un guion y números. Ejemplo: ABC-123'
            )
        ],
        widget=forms.TextInput(attrs={'class': 'form-control rounded-pill border-0 bg-light px-3', 'placeholder': 'Ej: TRAT-001'}),
        required=True
    )

    # 2. Validación de Nombre: Mínimo 5 letras, SIN caracteres especiales ni números
    # Explicación regex: ^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]{5,}$ (Solo letras y espacios, mínimo 5 caracteres)
    nombre_tratamiento = forms.CharField(
        validators=[
            RegexValidator(
                regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ ]{5,}$',
                message='El nombre debe tener mínimo 5 letras y no se permiten números ni caracteres especiales.'
            )
        ],
        widget=forms.TextInput(attrs={'class': 'form-control rounded-pill border-0 bg-light px-3', 'placeholder': 'Ej: Limpieza Dental'}),
        required=True
    )

    # 3. Descripción obligatoria
    descripcion = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control rounded-4 border-0 bg-light px-3', 'rows': 3, 'placeholder': 'Escriba la descripción aquí...'}),
        required=True
    )

    # 4. Costo Base: Enteros positivos únicamente
    costo_base = forms.IntegerField(
        min_value=1,
        error_messages={
            'invalid': 'Solo se aceptan números enteros.',
            'min_value': 'El costo debe ser un número entero mayor a cero.'
        },
        widget=forms.NumberInput(attrs={'class': 'form-control rounded-pill border-0 bg-light px-3', 'step': '1'}),
        required=True
    )

    # 5. Duración estimada: Enteros positivos únicamente
    duracion_estimada_minutos = forms.IntegerField(
        min_value=1,
        error_messages={
            'invalid': 'Solo se aceptan números enteros.',
            'min_value': 'La duración debe ser un número entero mayor a cero.'
        },
        widget=forms.NumberInput(attrs={'class': 'form-control rounded-pill border-0 bg-light px-3', 'step': '1'}),
        required=True
    )

    class Meta:
        model = Tratamiento
        fields = ['codigo', 'nombre_tratamiento', 'descripcion', 'costo_base', 'duracion_estimada_minutos']

    # Validación extra por si intentan meter decimales camuflados en el Costo Base
    def clean_costo_base(self):
        costo = self.cleaned_data.get('costo_base')
        if costo is not None and not isinstance(costo, int):
            raise ValidationError("No se aceptan decimales.")
        return costo