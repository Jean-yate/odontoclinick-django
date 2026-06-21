import datetime
from datetime import date
import re
from django import forms
from django.core.exceptions import ValidationError

from CuentasApp.models import Secretaria, Usuario, Rol, Estado
from MedicoApp.models import Medico
from PacienteApp.models import Paciente


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Asigne una contraseña segura'}),
        label="Contraseña",
        required=True
    )

    class Meta:
        model = Usuario
        fields = ['nombre', 'apellidos', 'nombre_usuario', 'correo', 'telefono', 'id_rol', 'id_estado', 'password']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_usuario': forms.TextInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'id_rol': forms.Select(attrs={'class': 'form-control'}),
            'id_estado': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')

        if not password and self.instance.pk:
            return password

        if len(password) < 8:
            raise ValidationError("🔒 La contraseña debe tener al menos 8 caracteres.")
        if not re.search(r'[A-Z]', password):
            raise ValidationError("🔠 La contraseña debe contener al menos una letra mayúscula.")
        if not re.search(r'[a-z]', password):
            raise ValidationError("🔡 La contraseña debe contener al menos una letra minúscula.")
        if not re.search(r'[0-9]', password):
            raise ValidationError("🔢 La contraseña debe incluir al menos un número.")
        if not re.search(r'[@$!%*?&._-]', password):
            raise ValidationError("🛡️ La contraseña debe incluir al menos un carácter especial (ej: @, $, !, %, *, ?, &, ., _, -).")

        return password

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
            raise ValidationError("👤 El nombre no puede contener números ni caracteres especiales.")
        return nombre

    def clean_apellidos(self):
        apellidos = self.cleaned_data.get('apellidos')
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', apellidos):
            raise ValidationError("👤 Los apellidos no pueden contener números ni caracteres especiales.")
        return apellidos

    def clean_correo(self):
        correo = self.cleaned_data.get('correo').lower()
        usuario_existente = Usuario.objects.filter(correo=correo)
        if self.instance.pk:
            usuario_existente = usuario_existente.exclude(pk=self.instance.pk)
        if usuario_existente.exists():
            raise ValidationError("📧 Este correo electrónico ya se encuentra registrado en el sistema.")
        return correo

    def clean_nombre_usuario(self):
        nombre_usuario = self.cleaned_data.get('nombre_usuario')
        if not re.match(r'^[a-zA-Z0-9_.-]+$', nombre_usuario):
            raise ValidationError("📛 El nombre de usuario solo admite letras, números, puntos, guiones y guiones bajos.")
        usuario_existente = Usuario.objects.filter(nombre_usuario=nombre_usuario)
        if self.instance.pk:
            usuario_existente = usuario_existente.exclude(pk=self.instance.pk)
        if usuario_existente.exists():
            raise ValidationError("🚫 Este nombre de usuario ya está en uso por otro colaborador.")
        return nombre_usuario

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if telefono:
            telefono_limpio = re.sub(r'[\s-]', '', telefono)
            if not telefono_limpio.isdigit():
                raise ValidationError("📞 El teléfono debe contener únicamente números.")
            if len(telefono_limpio) < 7 or len(telefono_limpio) > 15:
                raise ValidationError("📞 El número de teléfono debe tener una longitud válida (entre 7 y 15 dígitos).")
        return telefono


class MedicoExtraForm(forms.ModelForm):

    class Meta:
        model = Medico
        fields = [
            'id_especialidad',
            'licencia_medica',
            'anos_experiencia',
            'fecha_ingreso'
        ]
        widgets = {
            # ✅ Sin required — la validación se hace en la vista
            'id_especialidad': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'licencia_medica': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Licencia médica',
                }
            ),
            'anos_experiencia': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Años de experiencia'
                }
            ),
            'fecha_ingreso': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_especialidad'].empty_label = "Seleccione una especialidad..."
        self.fields['id_especialidad'].label = "Especialidad"
        self.fields['licencia_medica'].label = "Licencia Médica"
        self.fields['anos_experiencia'].label = "Años de Experiencia"
        self.fields['fecha_ingreso'].label = "Fecha de Ingreso"
        # ✅ Marcar todos los campos como no requeridos a nivel de formulario
        for field in self.fields.values():
            field.required = False

    def clean_licencia_medica(self):
        licencia = self.cleaned_data.get('licencia_medica')
        if not licencia:
            raise ValidationError("La licencia médica es obligatoria.")
        return licencia

    def clean_anos_experiencia(self):
        anos = self.cleaned_data.get('anos_experiencia')
        if anos is not None and anos < 0:
            raise ValidationError("Los años de experiencia no pueden ser negativos.")
        return anos


class SecretariaExtraForm(forms.ModelForm):

    class Meta:
        model = Secretaria
        fields = [
            'fecha_ingreso',
            'turno'
        ]
        widgets = {
            'fecha_ingreso': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            # ✅ Sin required — la validación se hace en la vista
            'turno': forms.Select(
                attrs={'class': 'form-select'}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ Marcar todos los campos como no requeridos a nivel de formulario
        for field in self.fields.values():
            field.required = False

    def clean_turno(self):
        turno = self.cleaned_data.get('turno')


class PacienteExtraForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            'fecha_nacimiento',
            'direccion',
            'eps',
            'rh',
            'alergias',
            'enfermedades_preexistentes',
            'contacto_emergencia_nombre',
            'contacto_emergencia_telefono'
        ]
        widgets = {
            # ✅ Sin required — la validación se hace en la vista
            'fecha_nacimiento': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'direccion': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'eps': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'rh': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'alergias': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'enfermedades_preexistentes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
            'contacto_emergencia_nombre': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            # ✅ Sin required — la validación se hace en la vista
            'contacto_emergencia_telefono': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ Marcar todos los campos como no requeridos a nivel de formulario
        for field in self.fields.values():
            field.required = False

    def clean_rh(self):
        rh = self.cleaned_data.get('rh')
        permitidos = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
        if rh and rh.upper() not in permitidos:
            raise ValidationError("RH inválido.")
        return rh.upper() if rh else rh

    def clean_contacto_emergencia_telefono(self):
        telefono = self.cleaned_data.get('contacto_emergencia_telefono')
        if telefono:
            telefono = telefono.replace(" ", "")
            if not telefono.isdigit():
                raise ValidationError("Solo números.")
            if len(telefono) < 7:
                raise ValidationError("Número demasiado corto.")
        return telefono

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if fecha:
            edad = date.today().year - fecha.year
            if edad > 120:
                raise ValidationError("Fecha de nacimiento inválida.")
            if fecha > date.today():
                raise ValidationError("No puede ser futura.")
        return fecha


class CambiarPasswordForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Escriba la nueva contraseña'}),
        label="Nueva Contraseña",
        required=True
    )
    confirmar_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repita la nueva contraseña'}),
        label="Confirmar Contraseña",
        required=True
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmar_password = cleaned_data.get("confirmar_password")

        if password and confirmar_password and password != confirmar_password:
            raise ValidationError("❌ Las contraseñas ingresadas no coinciden. Verifíquelas.")

        if password:
            if len(password) < 8:
                raise ValidationError("🔒 La contraseña debe tener al menos 8 caracteres.")
            if not re.search(r'[A-Z]', password):
                raise ValidationError("🔠 Debe contener al menos una letra mayúscula.")
            if not re.search(r'[0-9]', password):
                raise ValidationError("🔢 Debe incluir al menos un número.")
            if not re.search(r'[@$!%*?&._-]', password):
                raise ValidationError("🛡️ Debe incluir al menos un carácter especial.")

        return cleaned_data