import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.db.models.functions import ExtractMonth

# Modelos globales
from CuentasApp.models import Usuario, Secretaria, Rol, Estado
from MedicoApp.models import Medico, Disponibilidad
from PacienteApp.models import Paciente
from CitaApp.models import Cita 
from FacturacionApp.models import Pago
from InventarioApp.models import Producto

from .forms import (
    UsuarioForm,
    CambiarPasswordForm,
    MedicoExtraForm,
    SecretariaExtraForm,
    PacienteExtraForm
)

# =========================================================================
# --- DECORADOR O VERIFICACIÓN DE SEGURIDAD INTERNA ---
# =========================================================================
def es_administrador(user):
    return user.is_authenticated and hasattr(user, 'id_rol') and user.id_rol.nombre_rol == 'Administrador'


# =========================================================================
# --- PASO 3: DASHBOARD ADMINISTRATIVO CORREGIDO Y COMPLETO ---
# =========================================================================
@login_required
def dashboard_admin(request):
    # Restricción estricta de seguridad perimetral
    if not es_administrador(request.user):
        messages.error(request, "🛡️ Acceso denegado. No posees credenciales de Administrador.")
        return redirect('home')

    hoy = datetime.date.today()
    ayer = hoy - datetime.timedelta(days=1)
    mes_actual = hoy.month
    anio_actual = hoy.year

    # 1. CONTADORES GENERALES (Usuarios y Activos)
    total_usuarios = Usuario.objects.count()
    total_doctores = Usuario.objects.filter(id_rol__nombre_rol__icontains='doctor').count() or Usuario.objects.filter(id_rol__nombre_rol__icontains='medico').count()
    total_secretarias = Usuario.objects.filter(id_rol__nombre_rol__icontains='secretaria').count()
    total_pacientes = Paciente.objects.count()
    
    # Usuarios Activos / Inactivos basándose en el maestro de Estados
    usuarios_activos = Usuario.objects.filter(id_estado__nombre_estado__icontains='acti').count()
    usuarios_inactivos = total_usuarios - usuarios_activos

    # 2. OPERACIÓN CLÍNICA DIARIA (Citas Hoy vs Ayer)
    total_citas_hoy = Cita.objects.filter(fecha_hora__date=hoy).count()
    citas_ayer = Cita.objects.filter(fecha_hora__date=ayer).count()
    delta_citas = total_citas_hoy - citas_ayer

    canceladas_hoy = Cita.objects.filter(fecha_hora__date=hoy, id_estado_cita__nombre_estado__icontains='cancelada').count()
    canceladas_ayer = Cita.objects.filter(fecha_hora__date=ayer, id_estado_cita__nombre_estado__icontains='cancelada').count()
    delta_canceladas = canceladas_hoy - canceladas_ayer

    en_espera = Cita.objects.filter(fecha_hora__date=hoy, id_estado_cita__nombre_estado__icontains='espera').count()

    # 3. SECCIÓN FACTURACIÓN & METRICAS DE PAGO
    total_recaudado = Pago.objects.aggregate(total=Sum('monto'))['total'] or 0
    recaudado_mes_actual = Pago.objects.filter(fecha_pago__month=mes_actual, fecha_pago__year=anio_actual).aggregate(total=Sum('monto'))['total'] or 0
    recaudado_mes_anterior = Pago.objects.filter(fecha_pago__month=mes_actual-1 if mes_actual > 1 else 12, fecha_pago__year=anio_actual if mes_actual > 1 else anio_actual-1).aggregate(total=Sum('monto'))['total'] or 0
    
    # Delta porcentual de ingresos
    if recaudado_mes_anterior > 0:
        delta_ingresos = round(((recaudado_mes_actual - recaudado_mes_anterior) / recaudado_mes_anterior) * 100, 1)
    else:
        delta_ingresos = 100.0 if recaudado_mes_actual > 0 else 0.0

    # Estados de Pago para la Gráfica de Dona (Porcentajes)
    # 3. SECCIÓN FACTURACIÓN & METRICAS DE PAGO
    total_facturas = Pago.objects.count() or 1

    # Filtramos a través de la cita y el estado de la cita
    cant_pagadas = Pago.objects.filter(id_cita__id_estado_cita__nombre_estado__icontains='paga').count()
    cant_con_abono = Pago.objects.filter(id_cita__id_estado_cita__nombre_estado__icontains='abono').count()
    cant_vencidos = Pago.objects.filter(id_cita__id_estado_cita__nombre_estado__icontains='espera').count()

    pct_pagadas = round((cant_pagadas / total_facturas) * 100, 1)
    pct_con_abono = round((cant_con_abono / total_facturas) * 100, 1)
    pct_sin_pagar = round((cant_vencidos / total_facturas) * 100, 1)

    pct_pagadas = round((cant_pagadas / total_facturas) * 100, 1)
    pct_con_abono = round((cant_con_abono / total_facturas) * 100, 1)
    pct_sin_pagar = round((cant_vencidos / total_facturas) * 100, 1)

    # Pacientes registrados este mes
    pacientes_mes = Paciente.objects.filter(id_usuario__fecha_creacion__month=mes_actual, id_usuario__fecha_creacion__year=anio_actual).count()

    # 4. SECCIÓN INVENTARIO
    total_productos = Producto.objects.count()
    productos_criticos = Producto.objects.filter(stock_actual__lte=10, activo=1)
    conteo_criticos = productos_criticos.count()

    # 5. RENDIMIENTO Y CARGA LABORAL (Doctores Hoy)
    doctores_hoy = Cita.objects.filter(fecha_hora__date=hoy) \
        .values('id_doctor__id_usuario__nombre', 'id_doctor__id_usuario__apellidos') \
        .annotate(total=Count('id_cita')).order_by('-total')
    
    max_citas_doctor = max([d['total'] for d in doctores_hoy]) if doctores_hoy else 1

    # 6. DATOS PARA RENDIMIENTO SEMANAL (Gráfica de barras)
    # Mapeo básico simulado o adaptado (Lunes a Sábado) para ChartJS
    labels_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
    realizadas_sem = [Cita.objects.filter(id_estado_cita__nombre_estado__icontains='realizada').count()] * 6 # Mapeable con agregaciones por fecha si se requiere
    canceladas_sem = [Cita.objects.filter(id_estado_cita__nombre_estado__icontains='cancelada').count()] * 6

    # 7. FLUJO FINANCIERO ANUAL (Chart.js Line)
    pagos_por_mes = Pago.objects.filter(fecha_pago__year=anio_actual) \
        .annotate(mes=ExtractMonth('fecha_pago')) \
        .values('mes') \
        .annotate(total=Sum('monto')) \
        .order_by('mes')

    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    valores_meses = {i: 0.0 for i in range(1, 13)}
    for p in pagos_por_mes:
        if p['mes'] in valores_meses:
            valores_meses[p['mes']] = float(p['total'])

    chart_labels = meses_nombres
    chart_data = [valores_meses[i] for i in range(1, 13)]

    # 8. PRÓXIMAS CITAS Y LOGS GLOBALES
    citas_proximas = Cita.objects.filter(fecha_hora__date=hoy).select_related('id_paciente__id_usuario', 'id_doctor__id_usuario', 'id_estado_cita').order_by('fecha_hora')[:5]
    ultimos_usuarios = Usuario.objects.select_related('id_rol').order_by('-id_usuario')[:5]

    context = {
        'total_usuarios': total_usuarios,
        'total_doctores': total_doctores,
        'total_secretarias': total_secretarias,
        'total_pacientes': total_pacientes,
        'usuarios_activos': usuarios_activos,
        'usuarios_inactivos': usuarios_inactivos,
        'ultimos_usuarios': ultimos_usuarios,
        
        'total_citas_hoy': total_citas_hoy,
        'delta_citas': delta_citas,
        'canceladas_hoy': canceladas_hoy,
        'delta_canceladas': delta_canceladas,
        'en_espera': en_espera,
        'pacientes_mes': pacientes_mes,
        'citas_proximas': citas_proximas,
        
        'delta_ingresos': delta_ingresos,
        'cant_vencidos': cant_vencidos,
        'pct_pagadas': pct_pagadas,
        'pct_con_abono': pct_con_abono,
        'pct_sin_pagar': pct_sin_pagar,
        'recaudado_mes_actual': recaudado_mes_actual,
        
        'total_productos': total_productos,
        'productos_criticos': productos_criticos,
        'conteo_criticos': conteo_criticos,
        
        'doctores_hoy': doctores_hoy,
        'max_citas_doctor': max_citas_doctor,
        'labels_semana': labels_semana,
        'realizadas_sem': realizadas_sem,
        'canceladas_sem': canceladas_sem,
        
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    }
    return render(request, 'AdminApp/dashboard_admin.html', context)


# =========================================================================
# --- PASO 4: CRUD DE USUARIOS EN ADELANTE ---
# =========================================================================
def lista_usuarios(request):
    usuarios = Usuario.objects.all()
    roles_lista = Rol.objects.all()
    
    query = request.GET.get('q')
    rol_id = request.GET.get('rol')
    
    if query:
        usuarios = usuarios.filter(
            Q(nombre__icontains=query) | 
            Q(apellidos__icontains=query) | 
            Q(nombre_usuario__icontains=query)
        )
    if rol_id:
        usuarios = usuarios.filter(id_rol_id=rol_id)
        
    return render(request, 'AdminApp/usuarios/lista.html', {
        'usuarios': usuarios,
        'roles_lista': roles_lista
    })

@login_required
def crear_usuario(request):
    if not es_administrador(request.user):
        return redirect('home')

    medico_form = MedicoExtraForm()
    secretaria_form = SecretariaExtraForm()
    paciente_form = PacienteExtraForm()

    if request.method == 'POST':
        form = UsuarioForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Instanciamos el usuario sin guardarlo en BD todavía para obtener el Rol seleccionado
                    nuevo_usuario = form.save(commit=False)
                    
                    # Obtenemos el nombre del rol en minúsculas
                    rol = nuevo_usuario.id_rol.nombre_rol.lower()

                    # =========================================================
                    # 1. VALIDACIONES EN LA VISTA (Antes de guardar en la BD)
                    # =========================================================
                    if 'doctor' in rol or 'medico' in rol:
                        especialidad = request.POST.get('id_especialidad')
                        licencia = request.POST.get('licencia_medica')

                        if not especialidad:
                            raise Exception("Debe seleccionar una especialidad.")
                        if not licencia:
                            raise Exception("La licencia médica es obligatoria.")

                    elif 'secretaria' in rol:
                        turno = request.POST.get('turno')

                        if not turno:
                            raise Exception("Debe seleccionar un turno.")

                    elif 'paciente' in rol:
                        fecha_nacimiento = request.POST.get('fecha_nacimiento')
                        telefono_emergencia = request.POST.get('contacto_emergencia_telefono')

                        if not fecha_nacimiento:
                            raise Exception("La fecha de nacimiento es obligatoria.")
                        if not telefono_emergencia:
                            raise Exception("El teléfono de emergencia es obligatorio.")

                    # =========================================================
                    # 2. PROCESO DE GUARDADO SI PASÓ LAS VALIDACIONES
                    # =========================================================
                    # Hasheamos la contraseña y guardamos el usuario base
                    nuevo_usuario.set_password(form.cleaned_data['password'])
                    nuevo_usuario.save()

                    # Creación del perfil específico según el rol
                    if 'medico' in rol or 'doctor' in rol:
                        Medico.objects.create(
                            id_usuario=nuevo_usuario,
                            id_especialidad_id=request.POST.get('id_especialidad'),
                            licencia_medica=request.POST.get('licencia_medica'),
                            anos_experiencia=request.POST.get('anos_experiencia') or None,
                            fecha_ingreso=request.POST.get('fecha_ingreso') or None
                        )

                    elif 'secretaria' in rol:
                        Secretaria.objects.create(
                            id_usuario=nuevo_usuario,
                            fecha_ingreso=request.POST.get('fecha_ingreso') or None,
                            turno=request.POST.get('turno')
                        )

                    elif 'paciente' in rol:
                        Paciente.objects.create(
                            id_usuario=nuevo_usuario,
                            fecha_nacimiento=request.POST.get('fecha_nacimiento') or None,
                            direccion=request.POST.get('direccion'),
                            eps=request.POST.get('eps'),
                            rh=request.POST.get('rh'),
                            alergias=request.POST.get('alergias'),
                            enfermedades_preexistentes=request.POST.get('enfermedades_preexistentes'),
                            contacto_emergencia_nombre=request.POST.get('contacto_emergencia_nombre'),
                            contacto_emergencia_telefono=request.POST.get('contacto_emergencia_telefono')
                        )

                    messages.success(
                        request,
                        f"✅ Usuario '{nuevo_usuario.nombre_usuario}' guardado correctamente."
                    )
                    return redirect('admin_app:lista_usuarios')

            except Exception as e:
                # Si algo falla aquí adentro, no se guarda nada en la base de datos
                messages.error(
                    request,
                    f"❌ Error: {e}"
                )

        else:
            messages.error(
                request,
                "⚠ Corrige los errores del formulario."
            )

    else:
        form = UsuarioForm()

    return render(
        request,
        'AdminApp/usuarios/crear.html',
        {
            'form': form,
            'medico_form': medico_form,
            'secretaria_form': secretaria_form,
            'paciente_form': paciente_form,
        }
    )


@login_required
def editar_usuario(request, id_usuario):
    """Actualiza datos del perfil de un usuario existente sin alterar su contraseña"""
    if not es_administrador(request.user):
        return redirect('home')
        
    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        # Hacemos el password opcional al editar para evitar pisar el hash existente
        if 'password' in form.fields:
            form.fields['password'].required = False
            
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                messages.success(request, f"✅ Datos de '{usuario.nombre_usuario}' actualizados perfectamente.")
                return redirect('admin_app:lista_usuarios')
            except Exception as e:
                messages.error(request, f"❌ Error al salvar los cambios: {e}")
    else:
        form = UsuarioForm(instance=usuario)
        if 'password' in form.fields:
            form.fields['password'].required = False
        
    return render(request, 'AdminApp/usuarios/editar.html', {'form': form, 'usuario': usuario})


@login_required
def cambiar_estado(request, id_usuario):
    """Modifica dinámicamente el estado del usuario (Activación/Desactivación Lógica)"""
    if not es_administrador(request.user):
        return redirect('home')
        
    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)
    
    # Intentar ubicar los estados basados en tu maestro de Estados
    estado_activo = Estado.objects.filter(nombre_estado__icontains='Acti').first()
    estado_inactivo = Estado.objects.filter(nombre_estado__icontains='Inact').first()
    
    if usuario.id_estado == estado_activo:
        usuario.id_estado = estado_inactivo
        messages.warning(request, f"🚫 El usuario '{usuario.nombre_usuario}' ha sido desactivado del sistema.")
    else:
        usuario.id_estado = estado_activo
        messages.success(request, f"⚡ El usuario '{usuario.nombre_usuario}' ha sido reactivado exitosamente.")
        
    usuario.save()
    return redirect('admin_app:lista_usuarios')


# =========================================================================
# --- PASO 5: GESTIÓN INDEPENDIENTE DE CONTRASEÑAS ---
# =========================================================================
@login_required
def cambiar_password(request, id_usuario):
    """Sobreescribe de forma segura las llaves de seguridad"""
    if not es_administrador(request.user):
        return redirect('home')
        
    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)
    
    if request.method == 'POST':
        form = CambiarPasswordForm(request.POST)
        if form.is_valid():
            try:
                usuario.set_password(form.cleaned_data['password'])
                usuario.save()
                messages.success(request, f"🔑 Credencial de '{usuario.nombre_usuario}' modificada con éxito.")
                return redirect('admin_app:lista_usuarios')
            except Exception as e:
                messages.error(request, f"❌ Fallo al encriptar llave de ingreso: {e}")
    else:
        form = CambiarPasswordForm()
        
    return render(request, 'AdminApp/usuarios/password.html', {'form': form, 'usuario': usuario})


@login_required
def lista_roles(request):
    """Muestra el listado de roles junto con la métrica de usuarios asignados"""
    if not es_administrador(request.user):
        return redirect('home')
        
    # Anotamos dinámicamente cuántos usuarios tienen este rol asociado
    roles = Rol.objects.annotate(total_usuarios=Count('usuario')).order_by('nombre_rol')
    
    return render(request, 'AdminApp/roles/lista.html', {'roles': roles})


@login_required
def crear_rol(request):
    """Permite dar de alta nuevos roles en el ecosistema de la clínica"""
    if not es_administrador(request.user):
        return redirect('home')
        
    if request.method == 'POST':
        nombre_rol = request.POST.get('nombre_rol', '').strip()
        
        if not nombre_rol:
            messages.error(request, "⚠ El nombre del rol no puede enviarse vacío.")
        elif Rol.objects.filter(nombre_rol__iexact=nombre_rol).exists():
            messages.error(request, f"❌ El rol '{nombre_rol}' ya se encuentra registrado.")
        else:
            try:
                Rol.objects.create(nombre_rol=nombre_rol)
                messages.success(request, f"✅ El rol '{nombre_rol}' ha sido creado con éxito.")
                return redirect('admin_app:lista_roles')
            except Exception as e:
                messages.error(request, f"❌ Ocurrió un error al guardar el rol: {e}")
                
    return render(request, 'AdminApp/roles/crear.html')


@login_required
def editar_rol(request, id_rol):
    """Modifica el nombre identificador de un rol de acceso específico"""
    if not es_administrador(request.user):
        return redirect('home')
        
    rol = get_object_or_404(Rol, id_rol=id_rol)
    
    if request.method == 'POST':
        nombre_rol = request.POST.get('nombre_rol', '').strip()
        
        if not nombre_rol:
            messages.error(request, "⚠ El nombre del rol es mandatorio.")
        elif Rol.objects.filter(nombre_rol__iexact=nombre_rol).exclude(id_rol=id_rol).exists():
            messages.error(request, "❌ Ya existe otro rol con ese mismo nombre.")
        else:
            try:
                rol.nombre_rol = nombre_rol
                rol.save()
                messages.success(request, f"✅ El rol se ha actualizado a '{nombre_rol}'.")
                return redirect('admin_app:lista_roles')
            except Exception as e:
                messages.error(request, f"❌ Error al intentar guardar los cambios: {e}")
                
    return render(request, 'AdminApp/roles/crear.html', {'rol': rol})
