from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import update_session_auth_hash 
from .models import Usuario, Rol, Estado
from django.contrib.auth.password_validation import validate_password
from PacienteApp.models import Paciente 
import re
from django.core.exceptions import ValidationError
from datetime import date

# ---------------------------------------------------------
# 1. FORMULARIO DE LOGIN
# ---------------------------------------------------------
class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Nombre de usuario',
        'autocomplete': 'one-time-code'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Contraseña',
        'autocomplete': 'new-password'
    }))

# ---------------------------------------------------------
# 2. FORMULARIO DE REGISTRO GENERAL (USUARIO NUEVO)
# ---------------------------------------------------------
class RegistroForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña:", 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        validators=[validate_password] 
    )
    confirmar_password = forms.CharField(
        label="Confirmar contraseña:", 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'})
    )

    class Meta:
        model = Usuario
        fields = ['nombre_usuario', 'nombre', 'apellidos', 'correo', 'telefono']
        widgets = {
            'nombre_usuario': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 3001234567'}),
        }

    # Validación: Solo letras en Nombre y Apellidos
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre and not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
            raise ValidationError("El nombre solo debe contener letras.")
        return nombre

    def clean_apellidos(self):
        apellidos = self.cleaned_data.get('apellidos')
        if apellidos and not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', apellidos):
            raise ValidationError("Los apellidos solo deben contener letras.")
        return apellidos

    # Validación: Teléfono debe empezar por 3 y tener 10 dígitos
    def clean_telefono(self):
        tel = self.cleaned_data.get('telefono')
        if tel:
            if not re.match(r'^3\d{9}$', tel):
                raise ValidationError("El teléfono debe iniciar con '3' y tener exactamente 10 dígitos.")
        return tel

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("confirmar_password")
        if p1 and p2 and p1 != p2:
            self.add_error('confirmar_password', "Las contraseñas no coinciden.")
        return cleaned_data

# ---------------------------------------------------------
# 3. FORMULARIO DE DETALLES CLÍNICOS (PARA REGISTRO Y EDICIÓN)
# ---------------------------------------------------------
class RegistroPacienteForm(forms.ModelForm):
    fecha_nacimiento = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            format='%Y-%m-%d', 
            attrs={'class': 'form-control', 'type': 'date'}
        )
    )

    class Meta:
        model = Paciente
        fields = [
            'fecha_nacimiento', 'direccion', 'eps', 'rh', 
            'alergias', 'enfermedades_preexistentes', 
            'contacto_emergencia_nombre', 'contacto_emergencia_telefono'
        ]
        widgets = {
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'eps': forms.TextInput(attrs={'class': 'form-control'}),
            'rh': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: O+'}),
            'alergias': forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}),
            'enfermedades_preexistentes': forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}),
            'contacto_emergencia_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'contacto_emergencia_telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }

    # Validación: No permitir fechas de nacimiento futuras
    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if fecha and fecha > date.today():
            raise ValidationError("La fecha de nacimiento no puede ser posterior al día de hoy.")
        return fecha

    def clean_rh(self):
        rh = self.cleaned_data.get('rh')
        if rh is None: rh = ''
        rh = rh.upper()
        validos = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
        if rh and rh not in validos:
            raise ValidationError("RH no válido. Usa el formato Ej: O+")
        return rh

# ---------------------------------------------------------
# 4. FORMULARIO DE EDICIÓN ADMINISTRATIVA (SOLO CUENTA)
# ---------------------------------------------------------
class EditarPacienteForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre', 'apellidos', 'correo', 'telefono', 'id_estado']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'id_estado': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre and not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
            raise ValidationError("El nombre solo debe contener letras.")
        return nombre

    def clean_apellidos(self):
        apellidos = self.cleaned_data.get('apellidos')
        if apellidos and not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', apellidos):
            raise ValidationError("Los apellidos solo deben contener letras.")
        return apellidos

    def clean_telefono(self):
        tel = self.cleaned_data.get('telefono')
        if tel and not re.match(r'^3\d{9}$', tel):
            raise ValidationError("El teléfono debe iniciar con '3' y tener 10 dígitos.")
        return tel

# ---------------------------------------------------------
# 5. FORMULARIO DE AUTOGESTIÓN DE PERFIL (PARA EL PACIENTE)
# ---------------------------------------------------------
class EditarPerfilPacienteForm(forms.ModelForm):
    nombre = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellidos = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    correo = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'off'}))
    telefono = forms.CharField(max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 3001234567'}))

    fecha_nacimiento = forms.DateField(required=False, widget=forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}))
    direccion = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    eps = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    rh = forms.CharField(max_length=3, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: O+'}))
    alergias = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}))
    enfermedades_preexistentes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}))
    contacto_emergencia_nombre = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    contacto_emergencia_telefono = forms.CharField(max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    nueva_password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}), help_text="Dejar en blanco para no cambiar.")
    confirmar_password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}))

    class Meta:
        model = Usuario
        fields = ['nombre', 'apellidos', 'correo', 'telefono']

    def __init__(self, *args, **kwargs):
        self.paciente_instance = kwargs.pop('paciente_instance', None)
        super().__init__(*args, **kwargs)
        if self.paciente_instance:
            p = self.paciente_instance
            self.fields['direccion'].initial = p.direccion
            self.fields['eps'].initial = p.eps
            self.fields['rh'].initial = p.rh
            self.fields['alergias'].initial = p.alergias
            self.fields['enfermedades_preexistentes'].initial = p.enfermedades_preexistentes
            self.fields['contacto_emergencia_nombre'].initial = p.contacto_emergencia_nombre
            self.fields['contacto_emergencia_telefono'].initial = p.contacto_emergencia_telefono
            if p.fecha_nacimiento:
                self.fields['fecha_nacimiento'].initial = p.fecha_nacimiento.strftime('%Y-%m-%d')

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre and not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
            raise ValidationError("El nombre solo debe contener letras.")
        return nombre

    def clean_apellidos(self):
        apellidos = self.cleaned_data.get('apellidos')
        if apellidos and not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', apellidos):
            raise ValidationError("Los apellidos solo deben contener letras.")
        return apellidos

    def clean_telefono(self):
        tel = self.cleaned_data.get('telefono')
        if tel and not re.match(r'^3\d{9}$', tel):
            raise ValidationError("El teléfono debe iniciar con '3' y tener 10 dígitos.")
        return tel

    def clean_rh(self):
        rh = self.cleaned_data.get('rh', '').upper()
        if rh and rh not in ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']:
            raise ValidationError("RH no válido. Usa el formato Ej: O+")
        return rh

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("nueva_password")
        p2 = cleaned_data.get("confirmar_password")

        if p1:
            # Bloquear contraseña actual (Punto 5 Seguridad)
            if self.instance.pk and self.instance.check_password(p1):
                self.add_error('nueva_password', "La nueva contraseña no puede ser igual a la actual.")
            
            if p1 != p2:
                self.add_error('confirmar_password', "Las contraseñas no coinciden.")
            else:
                try:
                    validate_password(p1, self.instance)
                except ValidationError as e:
                    self.add_error('nueva_password', e)
        return cleaned_data

    def save(self, request=None, commit=True): 
        user = super().save(commit=False)
        pwd = self.cleaned_data.get("nueva_password")
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
            if pwd and request:
                update_session_auth_hash(request, user)
            if self.paciente_instance:
                p = self.paciente_instance
                p.direccion = self.cleaned_data.get('direccion')
                p.fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')
                p.eps = self.cleaned_data.get('eps')
                p.rh = self.cleaned_data.get('rh')
                p.alergias = self.cleaned_data.get('alergias')
                p.enfermedades_preexistentes = self.cleaned_data.get('enfermedades_preexistentes')
                p.contacto_emergencia_nombre = self.cleaned_data.get('contacto_emergencia_nombre')
                p.contacto_emergencia_telefono = self.cleaned_data.get('contacto_emergencia_telefono')
                p.save()
        return user