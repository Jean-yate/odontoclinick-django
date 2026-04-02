from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import update_session_auth_hash 
from .models import Usuario, Rol, Estado
from PacienteApp.models import Paciente 

# 1. Formulario de Login
class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}))

# 2. Formulario de Registro General
class RegistroForm(forms.ModelForm):
    password = forms.CharField(label="Contraseña:", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirmar_password = forms.CharField(label="Confirmar contraseña:", widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Usuario
        fields = ['nombre_usuario', 'nombre', 'apellidos', 'correo', 'telefono']
        widgets = {
            'nombre_usuario': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("confirmar_password")
        if p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data

# 3. Formulario de Registro de Detalles de Paciente
class RegistroPacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = ['fecha_nacimiento', 'direccion', 'eps', 'rh', 'alergias', 'enfermedades_preexistentes', 'contacto_emergencia_nombre', 'contacto_emergencia_telefono']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
        }

# 4. Formulario de Edición (Administrativo) - ESTE ES EL QUE DABA EL ERROR DE IMPORTACIÓN
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

# 5. Formulario de Perfil (El que usamos para el paciente mismo)
class EditarPerfilPacienteForm(forms.ModelForm):
    direccion = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    nueva_password = forms.CharField(
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Vacío para no cambiar'})
    )
    confirmar_password = forms.CharField(
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Usuario
        fields = ['nombre', 'apellidos', 'correo', 'telefono']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.paciente_instance = kwargs.pop('paciente_instance', None)
        super().__init__(*args, **kwargs)
        if self.paciente_instance:
            self.fields['direccion'].initial = self.paciente_instance.direccion

    def save(self, request, commit=True): 
        user = super().save(commit=False)
        pwd = self.cleaned_data.get("nueva_password")
        
        if pwd:
            user.set_password(pwd)
        
        if commit:
            user.save()
            if pwd:
                update_session_auth_hash(request, user)
                
            if self.paciente_instance:
                nueva_dir = self.cleaned_data.get('direccion')
                if nueva_dir is not None:
                    self.paciente_instance.direccion = nueva_dir
                    self.paciente_instance.save(update_fields=['direccion'])
        return user