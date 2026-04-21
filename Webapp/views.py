from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
import csv
import io
import openpyxl
import openpyxl
from datetime import datetime
from django.core.paginator import Paginator

from django.http import HttpResponse

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
        form = PQRSForm(request.POST, user=request.user)
        if form.is_valid():
            # Si está logueado usamos datos de sesión, si no, los del formulario
            if request.user.is_authenticated:
                nombre = f"{request.user.nombre} {request.user.apellidos}"
                email_usuario = request.user.correo
            else:
                nombre = form.cleaned_data.get('nombre')
                email_usuario = form.cleaned_data.get('email')
            
            tipo = form.cleaned_data['tipo']
            mensaje = form.cleaned_data['mensaje']

            # --- CORREOS ---
            asunto_clinica = f"NUEVA {tipo.upper()} - {nombre}"
            cuerpo_clinica = f"Se ha recibido una solicitud:\n\nNombre: {nombre}\nCorreo: {email_usuario}\nTipo: {tipo}\n\nMensaje:\n{mensaje}"
            
            asunto_usuario = f"Copia de su {tipo} - OdontoClinick"
            cuerpo_usuario = f"Hola {nombre},\n\nHemos recibido tu {tipo.lower()} con éxito. Pronto nos comunicaremos contigo.\n\nDetalles:\n\"{mensaje}\""

            try:
                # 1. Envío a la clínica
                send_mail(asunto_clinica, cuerpo_clinica, settings.EMAIL_HOST_USER, ['odontoclinick77@gmail.com'])
                
                # 2. Envío de copia al usuario
                if email_usuario:
                    send_mail(asunto_usuario, cuerpo_usuario, settings.EMAIL_HOST_USER, [email_usuario])
                
                messages.success(request, "✅ PQRS enviada con éxito. Revisa tu correo para ver la copia.")
                return redirect('home')
            except Exception as e:
                messages.error(request, f"❌ No se pudo enviar el correo: {e}")
    else:
        form = PQRSForm(user=request.user)
        
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
    pacientes_list = Usuario.objects.filter(id_rol__nombre_rol='Paciente').order_by('nombre')
    
    if query:
        pacientes_list = pacientes_list.filter(
            Q(nombre_usuario__icontains=query) | 
            Q(nombre__icontains=query) | 
            Q(apellidos__icontains=query)
        )
    
    # Paginación: 10 pacientes por página
    paginator = Paginator(pacientes_list, 10)
    page_number = request.GET.get('page')
    pacientes = paginator.get_page(page_number)
    
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
def carga_masiva_pacientes(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        archivo = request.FILES['archivo_excel']
        
        try:
            wb = openpyxl.load_workbook(archivo)
            hoja = wb.active
            creados = 0
            errores = 0

            rol_paciente = Rol.objects.get(nombre_rol='Paciente')
            estado_activo = Estado.objects.filter(nombre_estado__icontains='Acti').first()

            # Quitamos el transaction.atomic() de afuera para que si uno falla, 
            # los demás sí puedan procesarse individualmente.
            for fila in hoja.iter_rows(min_row=2, values_only=True):
                user_val = str(fila[0]) if fila[0] else None
                if not user_val: continue 

                try:
                    with transaction.atomic():
                        # 1. Intentamos obtener el usuario si ya existe, o crearlo si no.
                        # update_or_create evita el error de "Duplicate entry"
                        nuevo_u, created = Usuario.objects.update_or_create(
                            nombre_usuario=user_val,
                            defaults={
                                'nombre': fila[2],
                                'apellidos': fila[3],
                                'correo': fila[4],
                                'telefono': fila[5],
                                'id_rol': rol_paciente,
                                'id_estado': estado_activo,
                            }
                        )
                        
                        # Si es nuevo, le ponemos la contraseña del Excel
                        if created:
                            nuevo_u.set_password(str(fila[1]))
                            nuevo_u.save()

                        # 2. Intentamos crear o actualizar el perfil de Paciente
                        # Esto evita el error en la llave foránea id_usuario
                        Paciente.objects.update_or_create(
                            id_usuario=nuevo_u,
                            defaults={
                                'fecha_nacimiento': fila[6],
                                'direccion': fila[7],
                                'eps': fila[8],
                                'rh': fila[9],
                                'alergias': fila[10],
                                'enfermedades_preexistentes': fila[11],
                                'contacto_emergencia_nombre': fila[12],
                                'contacto_emergencia_telefono': fila[13]
                            }
                        )
                        creados += 1
                        
                except Exception as e:
                    print(f"Error procesando fila {user_val}: {e}")
                    errores += 1

            messages.success(request, f"Proceso finalizado. Procesados con éxito: {creados}. Errores: {errores}")
            return redirect('lista_pacientes')

        except Exception as e:
            messages.error(request, f"Error crítico al leer el archivo: {e}")

    return render(request, 'Webapp/carga_masiva.html')

@login_required
def detalle_paciente(request, id_usuario):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)
    paciente_clinico = get_object_or_404(Paciente, id_usuario=usuario)
    citas_recientes = Cita.objects.filter(id_paciente=paciente_clinico).order_by('-fecha_hora')[:5]
    return render(request, 'Webapp/detalle_paciente.html', {'u': usuario, 'p': paciente_clinico, 'citas': citas_recientes})



@login_required
def descargar_plantilla_pacientes(request):
    # Crear un nuevo libro de Excel
    wb = openpyxl.Workbook()
    hoja = wb.active
    hoja.title = "Plantilla_Pacientes"

    # Definir los encabezados (deben coincidir con el orden de tu vista de carga)
    encabezados = [
        'nombre_usuario', 'password', 'nombre', 'apellidos', 
        'correo', 'telefono', 'fecha_nacimiento', 'direccion', 
        'eps', 'rh', 'alergias', 'enfermedades_preexistentes', 
        'contacto_emergencia_nombre', 'contacto_emergencia_telefono'
    ]
    
    # Agregar los encabezados a la primera fila
    hoja.append(encabezados)

    # Opcional: Agregar una fila de ejemplo
    ejemplo = [
        '10102020', 'Pass123*', 'Juan', 'Perez', 
        'juan.perez@email.com', '3001234567', '1995-10-25', 'Calle 123', 
        'Sura', 'O+', 'Ninguna', 'Ninguna', 
        'Maria Perez', '3109876543'
    ]
    hoja.append(ejemplo)

    # Configurar la respuesta del navegador para descargar el archivo
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_pacientes_odontoclinick.xlsx'
    
    wb.save(response)
    return response