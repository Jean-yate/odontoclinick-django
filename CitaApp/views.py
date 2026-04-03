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
                # 1. Guardamos la Cita (Logística)
                cita = form.save(commit=False)
                cita.fecha_creacion = timezone.now()
                cita.fecha_actualizacion = timezone.now()
                cita.save()

                # 2. Recuperamos la nota del formulario (que no está en el modelo Cita)
                nota_paciente = form.cleaned_data.get('notas_paciente')

                # 3. CREAMOS el Historial Médico vinculado a esta cita
                # Aquí guardamos la nota para que el médico la vea después
                # 3. CREAMOS el Historial Médico con los nombres CORRECTOS
                HistorialMedico.objects.create(
                    id_cita=cita,
                    id_tratamento_id=1, # O el ID de un tratamiento por defecto (revisa el nombre id_treatmento)
                    costo_aplicado=0,    # Campo obligatorio en tu modelo
                    notas_paciente=nota_paciente,
                    diagnostico="Pendiente de evaluación",
                    # CAMBIO AQUÍ: 'observaciones_clinicas' en lugar de 'observaciones_tratamiento'
                    observaciones_clinicas="Cita agendada desde recepción",
                    # CAMBIO AQUÍ: No pases 'fecha' ni 'fecha_creacion' 
                    # porque tu modelo tiene auto_now_add=True (se pone sola)
                )
                messages.success(request, f'✅ Cita agendada y registro médico iniciado para {cita.id_paciente}')
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

