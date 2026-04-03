from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import Cita, EstadoCita 
from .forms import AgendarCitaForm
from FacturacionApp.models import Pago, MetodoPago 
from MedicoApp.models import HistorialMedico 

@login_required
def agendar_cita(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    if request.method == 'POST':
        form = AgendarCitaForm(request.POST)
        if form.is_valid():
            try:
                # 1. Guardamos solo la Cita (Logística básica)
                cita = form.save(commit=False)
                cita.fecha_creacion = timezone.now()
                cita.fecha_actualizacion = timezone.now()
                cita.save()
                
                messages.success(request, f'✅ Cita agendada con éxito para {cita.id_paciente}')
                return redirect('lista_citas') 
            except Exception as e:
                messages.error(request, f'❌ Error al procesar el agendamiento: {e}')
    else:
        form = AgendarCitaForm()
    
    return render(request, 'CitaApp/agendar_cita.html', {'form': form})

@login_required
def lista_citas(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    # Importante: Usamos select_related para mejorar el rendimiento de la DB
    citas = Cita.objects.all().order_by('-fecha_hora')
    return render(request, 'CitaApp/lista_citas.html', {'citas': citas})

@login_required
def cancelar_cita(request, id_cita):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    cita = get_object_or_404(Cita, pk=id_cita)
    try:
        estado_cancelado = EstadoCita.objects.get(nombre_estado='Cancelada')
        cita.id_estado_cita = estado_cancelado
        cita.fecha_actualizacion = timezone.now()
        cita.save()
        messages.success(request, f"✅ La cita de {cita.id_paciente} ha sido cancelada.")
    except EstadoCita.DoesNotExist:
        messages.error(request, "❌ Error: El estado 'Cancelada' no existe en la DB.")
    return redirect('lista_citas')

@login_required
def registrar_pago_cita(request, id_cita):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
        
    cita = get_object_or_404(Cita, pk=id_cita)
    metodos = MetodoPago.objects.filter(activo=1)

    if request.method == 'POST':
        try:
            metodo_id = request.POST.get('metodo')
            metodo = MetodoPago.objects.get(pk=metodo_id)
            
            Pago.objects.create(
                id_cita=cita,
                fecha_pago=timezone.now(),
                monto=request.POST.get('monto'),
                id_metodo_pago=metodo,
                referencia=request.POST.get('referencia'),
                notas=request.POST.get('notas')
            )
            messages.success(request, f"💰 Pago registrado para {cita.id_paciente}")
            return redirect('lista_citas')
        except Exception as e:
            messages.error(request, f"❌ Error al procesar pago: {e}")

    return render(request, 'FacturacionApp/generar_cobro.html', {'cita': cita, 'metodos': metodos})

@login_required
def agenda_diaria(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
    
    hoy = timezone.now().date()
    citas = Cita.objects.filter(fecha_hora__date=hoy).order_by('fecha_hora')
    return render(request, 'CitaApp/agenda_diaria.html', {'citas': citas})

# @login_required
# def agendar_cita(request):
#     if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
#         return redirect('home')

#     if request.method == 'POST':
#         form = AgendarCitaForm(request.POST)
#         if form.is_valid():
#             try:
#                 cita = form.save(commit=False)
#                 cita.fecha_creacion = timezone.now()
#                 cita.fecha_actualizacion = timezone.now()
#                 cita.save()
#                 messages.success(request, f'✅ Cita agendada para {cita.id_paciente}')
#                 return redirect('lista_citas') 
#             except Exception as e:
#                 messages.error(request, f'❌ Error de base de datos: {e}')
#     else:
#         form = AgendarCitaForm()
#     
#     return render(request, 'CitaApp/agendar_cita.html', {'form': form})

# @login_required
# def lista_citas(request):
#     if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
#         return redirect('home')

#     # Importante: Usamos select_related para mejorar el rendimiento de la DB
#     citas = Cita.objects.all().order_by('-fecha_hora')
#     return render(request, 'CitaApp/lista_citas.html', {'citas': citas})

