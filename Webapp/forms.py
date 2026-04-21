from django import forms

class PQRSForm(forms.Form):
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
        widget=forms.TextInput(attrs={'class': 'form-control form-control-glass', 'placeholder': 'Ej: Juan Pérez'})
    )
    email = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control form-control-glass', 'placeholder': 'tu@correo.com'})
    )
    tipo = forms.ChoiceField(
        label="Tipo de Solicitud",
        choices=TIPO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-control-glass'})
    )
    mensaje = forms.CharField(
        label="Descripción de tu mensaje",
        widget=forms.Textarea(attrs={'class': 'form-control form-control-glass', 'rows': 5, 'placeholder': 'Escribe aquí los detalles...'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(PQRSForm, self).__init__(*args, **kwargs)
        
        if user and user.is_authenticated:
            # Ocultamos y quitamos obligatoriedad porque usaremos los datos de la sesión
            self.fields['nombre'].widget = forms.HiddenInput()
            self.fields['email'].widget = forms.HiddenInput()
            self.fields['nombre'].required = False
            self.fields['email'].required = False