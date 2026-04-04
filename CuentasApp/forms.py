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
            'eps': forms.TextInput(attrs={'class': 'form-control'}),
            'rh': forms.TextInput(attrs={'class': 'form-control'}),
            'contacto_emergencia_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'contacto_emergencia_telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }

# 4. Formulario de Edición (Administrativo)
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

# 5. Formulario de Edición de Perfil (Propio del Paciente)
class EditarPerfilPacienteForm(forms.ModelForm):
    nombre = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellidos = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    correo = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    telefono = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    # FECHA CORREGIDA: Se añade format='%Y-%m-%d' para asegurar compatibilidad
    fecha_nacimiento = forms.DateField(
        required=False, 
        widget=forms.DateInput(
            format='%Y-%m-%d', 
            attrs={'class': 'form-control', 'type': 'date'}
        )
    )
    
    direccion = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    eps = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    rh = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: O+'}))
    alergias = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}))
    enfermedades_preexistentes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '2'}))
    contacto_emergencia_nombre = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    contacto_emergencia_telefono = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    nueva_password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirmar_password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Usuario
        fields = ['nombre', 'apellidos', 'correo', 'telefono']

    def __init__(self, *args, **kwargs):
        self.paciente_instance = kwargs.pop('paciente_instance', None)
        super().__init__(*args, **kwargs)
        
        if self.paciente_instance:
            # CORRECCIÓN DE FECHA: Formatear el valor inicial a string YYYY-MM-DD
            if self.paciente_instance.fecha_nacimiento:
                self.fields['fecha_nacimiento'].initial = self.paciente_instance.fecha_nacimiento.strftime('%Y-%m-%d')
            
            self.fields['direccion'].initial = self.paciente_instance.direccion
            self.fields['eps'].initial = self.paciente_instance.eps
            self.fields['rh'].initial = self.paciente_instance.rh
            self.fields['alergias'].initial = self.paciente_instance.alergias
            self.fields['enfermedades_preexistentes'].initial = self.paciente_instance.enfermedades_preexistentes
            self.fields['contacto_emergencia_nombre'].initial = self.paciente_instance.contacto_emergencia_nombre
            self.fields['contacto_emergencia_telefono'].initial = self.paciente_instance.contacto_emergencia_telefono

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("nueva_password")
        p2 = cleaned_data.get("confirmar_password")
        if p1 and p1 != p2:
            raise forms.ValidationError("Las nuevas contraseñas no coinciden.")
        return cleaned_data

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