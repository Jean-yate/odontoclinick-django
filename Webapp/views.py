from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

# Importaciones de modelos
from PacienteApp.models import Paciente
from CuentasApp.models import Usuario, Rol, Estado
from CitaApp.models import Cita 

# Importaciones de formularios
from .forms import PQRSForm 
from CuentasApp.forms import (
    RegistroForm, 
    RegistroPacienteForm, 
    EditarPacienteForm,
    EditarPerfilPacienteForm
)

# --- VISTAS PÚBLICAS ---

def home(request):
    """Vista principal - Asegúrate de que esta función exista para evitar el AttributeError"""
    return render(request, 'Webapp/index.html')

def contacto_pqrs(request):
    if request.method == 'POST':
        form = PQRSForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            email_usuario = form.cleaned_data['email']
            tipo = form.cleaned_data['tipo']
            mensaje = form.cleaned_data['mensaje']
            asunto = f"Nueva {tipo} de {nombre} - OdontoClinick"
            cuerpo = f"Nombre: {nombre}\nCorreo: {email_usuario}\nTipo: {tipo}\n\nMensaje:\n{mensaje}"
            try:
                send_mail(asunto, cuerpo, settings.EMAIL_HOST_USER, ['odontoclinick77@gmail.com'], fail_silently=False)
                messages.success(request, "¡Tu PQRS ha sido enviada con éxito!")
                return redirect('home')
            except Exception as e:
                messages.error(request, f"Error al enviar el correo: {e}")
    else:
        form = PQRSForm()
    return render(request, 'Webapp/pqrs.html', {'form': form})

# --- VISTAS PRIVADAS (GESTIÓN) ---

@login_required
def panel_secretaria(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
    total_pacientes = Usuario.objects.filter(id_rol__nombre_rol='Paciente').count()
    hoy = timezone.now().date()
    citas_hoy_count = Cita.objects.filter(fecha_hora__date=hoy).count()
    contexto = {
        'total_pacientes': total_pacientes,
        'citas_hoy_count': citas_hoy_count,
        'nombre_usuario': request.user.nombre,
    }
    return render(request, 'Webapp/panel_secretaria.html', contexto)

@login_required
def registro_integral_paciente(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
    if request.method == 'POST':
        form_user = RegistroForm(request.POST)
        form_paciente = RegistroPacienteForm(request.POST)
        if form_user.is_valid() and form_paciente.is_valid():
            try:
                with transaction.atomic():
                    nuevo_usuario = form_user.save(commit=False)
                    nuevo_usuario.id_rol = Rol.objects.get(nombre_rol='Paciente')
                    nuevo_usuario.id_estado = Estado.objects.filter(nombre_estado='Active').first() or Estado.objects.get(id_estado=1)
                    nuevo_usuario.save() 
                    paciente_instancia, _ = Paciente.objects.get_or_create(id_usuario=nuevo_usuario)
                    form_p_final = RegistroPacienteForm(request.POST, instance=paciente_instancia)
                    if form_p_final.is_valid():
                        form_p_final.save()
                    messages.success(request, f"Paciente {nuevo_usuario.nombre} registrado correctamente.")
                    return redirect('lista_pacientes')
            except Exception as e:
                messages.error(request, f"Error: {e}")
    else:
        form_user = RegistroForm()
        form_paciente = RegistroPacienteForm()
    return render(request, 'Webapp/registrar_paciente.html', {'form_user': form_user, 'form_paciente': form_paciente})

@login_required
def lista_pacientes(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
    query = request.GET.get('q')
    pacientes = Usuario.objects.filter(id_rol__nombre_rol='Paciente')
    if query:
        pacientes = pacientes.filter(Q(nombre_usuario__icontains=query) | Q(nombre__icontains=query) | Q(apellidos__icontains=query))
    return render(request, 'Webapp/lista_pacientes.html', {'pacientes': pacientes, 'query': query})

@login_required
def editar_paciente(request, id_usuario):
    """Edición corregida: Usa QuerySet.update para evitar conflictos con el modelo Usuario"""
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    usuario_instancia = get_object_or_404(Usuario, id_usuario=id_usuario)
    paciente_instancia = get_object_or_404(Paciente, id_usuario=usuario_instancia)
    
    if request.method == 'POST':
        form_user = EditarPacienteForm(request.POST, instance=usuario_instancia)
        form_clinico = RegistroPacienteForm(request.POST, instance=paciente_instancia)
        
        # Desactivamos validación de campos que no están en el formulario
        if 'id_estado' in form_user.fields: form_user.fields['id_estado'].required = False
        if 'id_rol' in form_user.fields: form_user.fields['id_rol'].required = False

        if form_user.is_valid() and form_clinico.is_valid():
            try:
                with transaction.atomic():
                    # 1. Obtenemos los datos limpios del formulario de Usuario
                    datos_usuario = form_user.cleaned_data
                    
                    # 2. Actualizamos mediante QuerySet.update() 
                    # Esto salta el método save() del modelo y escribe directo en la DB
                    Usuario.objects.filter(id_usuario=id_usuario).update(
                        nombre=datos_usuario.get('nombre', usuario_instancia.nombre),
                        apellidos=datos_usuario.get('apellidos', usuario_instancia.apellidos),
                        nombre_usuario=datos_usuario.get('nombre_usuario', usuario_instancia.nombre_usuario),
                        correo=datos_usuario.get('correo', usuario_instancia.correo),
                        telefono=datos_usuario.get('telefono', usuario_instancia.telefono),
                    )
                    
                    # 3. Guardamos los datos clínicos normalmente
                    form_clinico.save()
                    
                messages.success(request, f"¡Paciente {usuario_instancia.nombre} actualizado!")
                return redirect('lista_pacientes')
            except Exception as e:
                print(f"DEBUG ERROR: {e}")
                messages.error(request, f"Error técnico: {e}")
        else:
            messages.error(request, "Error en los datos. Revisa el formulario.")
    else:
        form_user = EditarPacienteForm(instance=usuario_instancia)
        form_clinico = RegistroPacienteForm(instance=paciente_instancia)
    
    return render(request, 'Webapp/editar_paciente.html', {
        'form_user': form_user, 'form_clinico': form_clinico, 'paciente': usuario_instancia
    })

@login_required
def detalle_paciente(request, id_usuario):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)
    paciente_clinico = get_object_or_404(Paciente, id_usuario=usuario)
    citas_recientes = Cita.objects.filter(id_paciente=paciente_clinico).order_by('-fecha_hora')[:5]
    return render(request, 'Webapp/detalle_paciente.html', {'u': usuario, 'p': paciente_clinico, 'citas': citas_recientes})