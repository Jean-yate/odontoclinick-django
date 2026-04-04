from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.db.models import Q 
from datetime import datetime

# Importaciones de modelos y formularios
from .models import Cita, EstadoCita 
from .forms import AgendarCitaForm
from FacturacionApp.models import Pago, MetodoPago 
from MedicoApp.models import HistorialMedico 

# --- GESTIÓN DE CITAS ---

@login_required
def agendar_cita(request):
    """
    Crea una nueva cita uniendo los campos de fecha y hora 
    que vienen separados desde el frontend dinámico.
    """
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    if request.method == 'POST':
        form = AgendarCitaForm(request.POST)
        # Capturamos los datos enviados manualmente por el JS/HTML
        fecha_solo = request.POST.get('fecha_seleccionada')
        hora_solo = request.POST.get('hora_seleccionada')

        if form.is_valid():
            if not fecha_solo or not hora_solo:
                messages.error(request, "❌ Debes seleccionar una fecha y una hora disponible.")
                return render(request, 'CitaApp/agendar_cita.html', {'form': form})

            try:
                # Unimos la fecha y la hora en un solo objeto datetime
                fecha_hora_str = f"{fecha_solo} {hora_solo}"
                fecha_hora_obj = datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M')

                # Guardamos con commit=False para asignar la fecha calculada
                cita = form.save(commit=False)
                cita.fecha_hora = fecha_hora_obj
                cita.save()

                messages.success(request, f'✅ Cita agendada para el {fecha_solo} a las {hora_solo}.')
                return redirect('lista_citas') 
            except Exception as e:
                messages.error(request, f'❌ Error al procesar la cita: {e}')
    else:
        form = AgendarCitaForm()
    
    return render(request, 'CitaApp/agendar_cita.html', {
        'form': form,
        'hoy': timezone.now().date()
    })

@login_required
def lista_citas(request):
    busqueda = request.GET.get('buscar')
    citas = Cita.objects.all().select_related(
        'id_paciente__id_usuario', 
        'id_doctor__id_usuario', 
        'id_estado_cita'
    ).order_by('-fecha_hora')

    if busqueda:
        citas = citas.filter(
            Q(id_paciente__id_usuario__nombre__icontains=busqueda) | 
            Q(id_paciente__id_usuario__apellidos__icontains=busqueda) |
            Q(id_doctor__id_usuario__nombre__icontains=busqueda) |
            Q(id_doctor__id_usuario__apellidos__icontains=busqueda) |
            Q(fecha_hora__icontains=busqueda)
        )

    estados_disponibles = EstadoCita.objects.all()

    return render(request, 'CitaApp/lista_citas.html', {
        'citas': citas,
        'estados_disponibles': estados_disponibles,
        'busqueda': busqueda
    })

@login_required
def agenda_diaria(request):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
    
    hoy = timezone.now().date()
    citas = Cita.objects.filter(fecha_hora__date=hoy).select_related(
        'id_paciente', 'id_doctor', 'id_estado_cita', 'id_paciente__id_usuario'
    ).order_by('fecha_hora')
    
    return render(request, 'CitaApp/agenda_diaria.html', {'citas': citas, 'hoy': hoy})

@login_required
def actualizar_estado_gestion(request, id_cita):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    if request.method == 'POST':
        cita = get_object_or_404(Cita, pk=id_cita)
        nuevo_estado_id = request.POST.get('id_estado')
        
        if nuevo_estado_id:
            nuevo_estado = get_object_or_404(EstadoCita, pk=nuevo_estado_id)
            cita.id_estado_cita = nuevo_estado
            cita.save()
            messages.success(request, f"✅ Estado actualizado: {nuevo_estado}")
        
    return redirect('lista_citas')

@login_required
def cancelar_cita(request, id_cita):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')

    cita = get_object_or_404(Cita, pk=id_cita)
    estado_cancelado = EstadoCita.objects.filter(nombre_estado__icontains='Cancelada').first()
    
    if estado_cancelado:
        cita.id_estado_cita = estado_cancelado
        cita.save()
        messages.success(request, f"✅ Cita de {cita.id_paciente} cancelada.")
    else:
        messages.error(request, "❌ Error: El estado 'Cancelada' no existe en la base de datos.")
    
    return redirect('lista_citas')

# --- GESTIÓN DE PAGOS Y FACTURACIÓN ---

@login_required
def registrar_pago_cita(request, id_cita):
    if request.user.id_rol.nombre_rol not in ['Secretaria', 'Administrador']:
        return redirect('home')
        
    cita = get_object_or_404(Cita, pk=id_cita)
    metodos = MetodoPago.objects.filter(activo=1)

    if request.method == 'POST':
        try:
            monto_input = request.POST.get('monto', '0').replace(',', '.')
            monto_pago = float(monto_input)

            if monto_pago > cita.saldo_pendiente:
                messages.warning(request, f"⚠️ El abono (${monto_pago}) excede el saldo (${cita.saldo_pendiente}).")
                return redirect('registrar_pago_cita', id_cita=id_cita)

            if monto_pago <= 0:
                messages.error(request, "❌ El monto debe ser mayor a cero.")
                return redirect('registrar_pago_cita', id_cita=id_cita)

            with transaction.atomic():
                Pago.objects.create(
                    id_cita=cita,
                    fecha_pago=timezone.now(),
                    monto=monto_pago,
                    id_metodo_pago_id=request.POST.get('metodo'),
                    referencia=request.POST.get('referencia'),
                    notas=request.POST.get('notas')
                )
                cita.refresh_from_db()
                messages.success(request, f"💰 Pago de ${monto_pago} guardado. Nuevo saldo: ${cita.saldo_pendiente}")
            
            return redirect('lista_citas')

        except ValueError:
            messages.error(request, "❌ Por favor ingresa un número válido en el monto.")
        except Exception as e:
            messages.error(request, f"❌ Error: {e}")

    context = {
        'cita': cita,
        'metodos': metodos,
        'total_abonado': cita.total_abonado,
        'saldo_pendiente': cita.saldo_pendiente,
        'costo_final': cita.costo_final
    }
    return render(request, 'FacturacionApp/generar_cobro.html', context)

@login_required
def ver_factura_cita(request, id_cita):
    cita = get_object_or_404(Cita, pk=id_cita)
    pagos = Pago.objects.filter(id_cita=cita).order_by('-fecha_pago')
    
    return render(request, 'FacturacionApp/factura_pos.html', {
        'cita': cita,
        'pagos': pagos,
        'hoy': timezone.now(),
    })