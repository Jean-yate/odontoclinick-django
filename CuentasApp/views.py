from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import LoginForm, RegistroForm
from .models import Usuario, Rol, Estado
from django.contrib import messages
from PacienteApp.models import Paciente
from .models import Secretaria
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # --- VALIDACIÓN DE ESTADO ---
            # Verificamos si el estado asociado es 'Activo'
            if user.id_estado and user.id_estado.nombre_estado != 'Activo':
                messages.error(request, "Tu cuenta está inactiva. Por favor, contacta al administrador.")
                return render(request, 'CuentasApp/login.html', {'form': form})
            
            # Si pasa la validación, procedemos al login
            login(request, user)
            
            rol = user.id_rol.nombre_rol
            if rol == 'Administrador':
                return redirect('/admin/') 
            elif rol == 'Secretaria':
                return redirect('panel_secretaria')
            elif rol == 'Paciente':
                return redirect('perfil_paciente')
            elif rol == 'Medico':
                return redirect('dashboard_medico')
            else:
                return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'CuentasApp/login.html', {'form': form})

def registro_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            # Usamos commit=False para procesar datos antes de guardar en MariaDB
            usuario = form.save(commit=False)
            
            # ASIGNACIÓN AUTOMÁTICA DE ROLES
            rol_paciente, _ = Rol.objects.get_or_create(nombre_rol='Paciente')
            # Asegúrate de que el ID 1 sea el activo o búscalo por nombre
            estado_activo, _ = Estado.objects.get_or_create(nombre_estado='Activo')
            
            usuario.id_rol = rol_paciente
            usuario.id_estado = estado_activo
            
            # IMPORTANTE: Encriptación de contraseña
            usuario.set_password(form.cleaned_data['password'])
            usuario.save()
            
            # Las señales (Signals) que creamos antes se encargarán 
            # de crear el registro en la tabla Paciente automáticamente.
            
            login(request, usuario)
            return redirect('perfil_paciente')
    else:
        form = RegistroForm()
    
    return render(request, 'CuentasApp/registro.html', {'form': form})

@login_required
def perfil_secretaria(request):
    if request.user.id_rol.nombre_rol != 'Secretaria':
        return redirect('home')

    secretaria = Secretaria.objects.filter(id_usuario=request.user).first()

    if request.method == 'POST':
        nuevo_password = request.POST.get('password')
        
        # 1. Si el usuario escribió algo en el campo de contraseña
        if nuevo_password and nuevo_password.strip():
            request.user.set_password(nuevo_password)
            request.user.save()
            # Esto evita que se cierre la sesión al cambiar la clave
            update_session_auth_hash(request, request.user)
            messages.success(request, "Contraseña actualizada correctamente.")
        
        # Aquí podrías guardar otros cambios (como el email si lo permites)
        messages.info(request, "Perfil visualizado/actualizado.")
        return redirect('perfil_secretaria')

    return render(request, 'CuentasApp/Administracion/perfil_secretaria.html', {
        'secretaria': secretaria
    })