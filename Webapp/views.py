from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages

# Importaciones correctas desde sus respectivas Apps
from PacienteApp.models import Paciente
from CuentasApp.models import Usuario, Rol, Estado
from CuentasApp.forms import EditarPacienteForm, RegistroForm, RegistroPacienteForm
from CitaApp.models import Cita 
from CitaApp.forms import AgendarCitaForm
from CuentasApp.forms import (
    EditarPacienteForm, 
    RegistroForm, 
    RegistroPacienteForm, 
    EditarPerfilPacienteForm # Añade este nuevo
)

def home(request):
    return render(request, 'Webapp/index.html')

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

# --- VISTA DE REGISTRO ÚNICO CORREGIDA ---
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
                    # 1. Crear el Usuario en CuentasApp
                    nuevo_usuario = form_user.save(commit=False)
                    nuevo_usuario.set_password(form_user.cleaned_data['password'])
                    
                    rol_paciente = Rol.objects.get(nombre_rol='Paciente')
                    estado_activo = Estado.objects.filter(nombre_estado='Active').first() or Estado.objects.get(id_estado=1)
                    
                    nuevo_usuario.id_rol = rol_paciente
                    nuevo_usuario.id_estado = estado_activo
                    nuevo_usuario.save() # Aquí la SIGNAL de CuentasApp crea el Paciente en PacienteApp

                    # 2. Manejar el modelo Paciente de PacienteApp
                    # Buscamos el paciente que la señal acaba de crear
                    paciente_instancia = Paciente.objects.get(id_usuario=nuevo_usuario)
                    
                    # Actualizamos esa instancia con los datos médicos (EPS, RH, etc.)
                    form_p_final = RegistroPacienteForm(request.POST, instance=paciente_instancia)
                    if form_p_final.is_valid():
                        paciente_data = form_p_final.save(commit=False)
                        # Asignamos la fecha de registro que tu modelo Paciente requiere
                        paciente_data.fecha_registro = timezone.now()
                        paciente_data.save()

                    messages.success(request, f"Paciente {nuevo_usuario.nombre} registrado correctamente.")
                    return redirect('lista_pacientes')
            except Exception as e:
                messages.error(request, f"Error al guardar en base de datos: {e}")
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form_user = RegistroForm()
        form_paciente = RegistroPacienteForm()

    return render(request, 'Webapp/registrar_paciente.html', {
        'form_user': form_user,
        'form_paciente': form_paciente
    })

@login_required
def lista_pacientes(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
    query = request.GET.get('q')
    pacientes = Usuario.objects.filter(id_rol__nombre_rol='Paciente')
    if query:
        pacientes = pacientes.filter(
            Q(nombre_usuario__icontains=query) | Q(nombre__icontains=query) | Q(apellidos__icontains=query)
        )
    return render(request, 'Webapp/lista_pacientes.html', {'pacientes': pacientes, 'query': query})

@login_required
def editar_paciente(request, id_usuario):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    usuario_instancia = get_object_or_404(Usuario, id_usuario=id_usuario)
    # Obtenemos la instancia de Paciente asociada a ese usuario
    paciente_instancia = get_object_or_404(Paciente, id_usuario=usuario_instancia)
    
    if request.method == 'POST':
        form_user = EditarPacienteForm(request.POST, instance=usuario_instancia)
        form_clinico = EditarPerfilPacienteForm(request.POST, instance=paciente_instancia)
        
        if form_user.is_valid() and form_clinico.is_valid():
            with transaction.atomic():
                form_user.save()
                form_clinico.save()
            messages.success(request, f"¡Paciente {usuario_instancia.nombre} actualizado con éxito!")
            return redirect('lista_pacientes')
    else:
        form_user = EditarPacienteForm(instance=usuario_instancia)
        form_clinico = EditarPerfilPacienteForm(instance=paciente_instancia)
    
    return render(request, 'Webapp/editar_paciente.html', {
        'form_user': form_user,
        'form_clinico': form_clinico,
        'paciente': usuario_instancia
    })

@login_required
def detalle_paciente(request, id_usuario):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)
    paciente_clinico = get_object_or_404(Paciente, id_usuario=usuario)
    
    # Traemos las últimas 5 citas para el historial rápido
    citas_recientes = Cita.objects.filter(id_paciente=paciente_clinico).order_by('-fecha_hora')[:5]

    return render(request, 'Webapp/detalle_paciente.html', {
        'u': usuario,
        'p': paciente_clinico,
        'citas': citas_recientes
    })