from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import update_session_auth_hash 
from .models import Usuario, Rol, Estado
from django.contrib.auth.password_validation import validate_password
from PacienteApp.models import Paciente 
import re
from django.core.exceptions import ValidationError
# ---------------------------------------------------------
# 1. FORMULARIO DE LOGIN
# ---------------------------------------------------------
class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Nombre de usuario',
        'autocomplete': 'one-time-code'  # Truco: 'one-time-code' suele romper el autocompletado
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Contraseña',
        'autocomplete': 'new-password' # Indica que no debe sugerir claves viejas
    }))

# ---------------------------------------------------------
# 2. FORMULARIO DE REGISTRO GENERAL (USUARIO NUEVO)
# ---------------------------------------------------------
class RegistroForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña:", 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        # Agregamos los validadores de seguridad de Django aquí:
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
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("confirmar_password")

        # 1. Validar que coincidan
        if p1 and p2 and p1 != p2:
            self.add_error('confirmar_password', "Las contraseñas no coinciden.")
        
        return cleaned_data

# ---------------------------------------------------------
# 3. FORMULARIO DE DETALLES CLÍNICOS (PARA REGISTRO Y EDICIÓN)
# ---------------------------------------------------------
class RegistroPacienteForm(forms.ModelForm):
    # Definir el campo aquí permite forzar el formato de entrada del navegador
    fecha_nacimiento = forms.DateField(
        required=False,
        input_formats=['%Y-%m-%d'],  # Formato estándar de HTML5 <input type="date">
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

    # Validación extra para el RH (opcional pero recomendada)
    def clean_rh(self):
        rh = self.cleaned_data.get('rh', '').upper()
        if rh and rh not in ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']:
            raise forms.ValidationError("Formato de RH no válido.")
        return rh

# ---------------------------------------------------------
# 4. FORMULARIO DE EDICIÓN ADMINISTRATIVA (SOLO CUENTA)
# ---------------------------------------------------------
class EditarPacienteForm(forms.ModelForm):
    class Meta:
        model = Usuario
        # Excluimos nombre_usuario para evitar errores de integridad
        fields = ['nombre', 'apellidos', 'correo', 'telefono', 'id_estado']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'id_estado': forms.Select(attrs={'class': 'form-select'}),
        }

# ---------------------------------------------------------
# 5. FORMULARIO DE AUTOGESTIÓN DE PERFIL (PARA EL PACIENTE)
# ---------------------------------------------------------
class EditarPerfilPacienteForm(forms.ModelForm):
    # Campos de Usuario (con validaciones de longitud)
    nombre = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    apellidos = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    correo = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )
    telefono = forms.CharField(
        max_length=15,
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 3001234567'})
    )

    # Campos de Paciente
    fecha_nacimiento = forms.DateField(
        required=False, 
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'})
    )
    direccion = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    eps = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    rh = forms.CharField(max_length=3, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: O+'}))
    alergias = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}))
    enfermedades_preexistentes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}))
    contacto_emergencia_nombre = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    contacto_emergencia_telefono = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    # Seguridad
    nueva_password = forms.CharField(
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        help_text="Dejar en blanco para no cambiar."
    )
    confirmar_password = forms.CharField(
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'})
    )

    class Meta:
        model = Usuario # Asegúrate de que 'Usuario' sea tu modelo CustomUser
        fields = ['nombre', 'apellidos', 'correo', 'telefono']

    def __init__(self, *args, **kwargs):
        self.paciente_instance = kwargs.pop('paciente_instance', None)
        super().__init__(*args, **kwargs)
        
        # Cargar datos iniciales del perfil médico
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
                # El widget 'date' requiere formato YYYY-MM-DD
                self.fields['fecha_nacimiento'].initial = p.fecha_nacimiento.strftime('%Y-%m-%d')

    def clean_telefono(self):
        tel = self.cleaned_data.get('telefono')
        if tel and not re.match(r'^\+?1?\d{7,15}$', tel):
            raise ValidationError("Ingresa un número de teléfono válido.")
        return tel

    def clean_rh(self):
        rh = self.cleaned_data.get('rh', '').upper()
        validos = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
        if rh and rh not in validos:
            raise ValidationError("RH no válido. Usa el formato Ej: O+")
        return rh

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("nueva_password")
        p2 = cleaned_data.get("confirmar_password")

        # Validar coincidencia y complejidad de contraseña
        if p1:
            if p1 != p2:
                self.add_error('confirmar_password', "Las contraseñas no coinciden.")
            else:
                try:
                    # Aplica validadores de Django (longitud, similitud, etc.)
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
            # IMPORTANTE: Actualizar sesión para no desloguear al usuario
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