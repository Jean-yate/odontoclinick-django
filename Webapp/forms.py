from django import forms

class PQRSForm(forms.Form):
    # Definimos las opciones para el selector
    TIPO_CHOICES = [
        ('', 'Selecciona una opción...'),
        ('Petición', 'Petición'),
        ('Queja', 'Queja'),
        ('Reclamo', 'Reclamo'),
        ('Sugerencia', 'Sugerencia'),
    ]

    nombre = forms.CharField(
        label="Nombre Completo",
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-glass',
            'placeholder': 'Ej: Juan Pérez'
        })
    )
    
    email = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-glass',
            'placeholder': 'tu@correo.com'
        })
    )
    
    tipo = forms.ChoiceField(
        label="Tipo de Solicitud",
        choices=TIPO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select form-control-glass'
        })
    )
    
    mensaje = forms.CharField(
        label="Descripción de tu mensaje",
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-glass',
            'rows': 5,
            'placeholder': 'Escribe aquí los detalles...'
        })
    )