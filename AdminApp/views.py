import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.db.models.functions import ExtractMonth, TruncDate, ExtractHour, ExtractWeekDay
 
# Modelos globales
from CuentasApp.models import Usuario, Secretaria, Rol, Estado
from MedicoApp.models import Medico, Disponibilidad
from PacienteApp.models import Paciente
from CitaApp.models import Cita
from FacturacionApp.models import Pago
from InventarioApp.models import Producto, MovimientoInventario
 
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
 
    # FIX: el 'or' original solo contaba un grupo si el primero daba 0.
    # Si ambos roles ("doctor" y "medico") existen con usuarios propios,
    # se perdía la suma. Usamos Q para contar la unión real.
    total_doctores = Usuario.objects.filter(
        Q(id_rol__nombre_rol__icontains='doctor') | Q(id_rol__nombre_rol__icontains='medico')
    ).distinct().count()
 
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
 
    # 3. SECCIÓN FACTURACIÓN & MÉTRICAS DE PAGO
    recaudado_mes_actual = Pago.objects.filter(
        fecha_pago__month=mes_actual, fecha_pago__year=anio_actual
    ).aggregate(total=Sum('monto'))['total'] or 0
 
    mes_anterior = mes_actual - 1 if mes_actual > 1 else 12
    anio_mes_anterior = anio_actual if mes_actual > 1 else anio_actual - 1
    recaudado_mes_anterior = Pago.objects.filter(
        fecha_pago__month=mes_anterior, fecha_pago__year=anio_mes_anterior
    ).aggregate(total=Sum('monto'))['total'] or 0
 
    # Delta porcentual de ingresos
    if recaudado_mes_anterior > 0:
        delta_ingresos = round(((recaudado_mes_actual - recaudado_mes_anterior) / recaudado_mes_anterior) * 100, 1)
    else:
        delta_ingresos = 100.0 if recaudado_mes_actual > 0 else 0.0
 
    # Estados de pago para la gráfica de dona (porcentajes).
    # NOTA: esto clasifica por el estado de la CITA (icontains sobre nombre_estado),
    # no por el saldo real (Pago vs costo_final que ya tienes en Cita.estado_pago).
    # Lo dejo como estaba para no romper tu fuente de datos actual, pero el modelo
    # Cita ya trae una property `estado_pago` más confiable si quieres migrar esto
    # a futuro (evita depender de que el estado de la cita se llame "paga"/"abono").
    total_facturas = Pago.objects.count() or 1
 
    cant_pagadas = Pago.objects.filter(id_cita__id_estado_cita__nombre_estado__icontains='paga').count()
    cant_con_abono = Pago.objects.filter(id_cita__id_estado_cita__nombre_estado__icontains='abono').count()
    cant_vencidos = Pago.objects.filter(id_cita__id_estado_cita__nombre_estado__icontains='espera').count()
 
    pct_pagadas = round((cant_pagadas / total_facturas) * 100, 1)
    pct_con_abono = round((cant_con_abono / total_facturas) * 100, 1)
    pct_sin_pagar = round((cant_vencidos / total_facturas) * 100, 1)
 
    # Pacientes registrados este mes
    pacientes_mes = Paciente.objects.filter(
        id_usuario__fecha_creacion__month=mes_actual, id_usuario__fecha_creacion__year=anio_actual
    ).count()
 
    # 4. SECCIÓN INVENTARIO
    total_productos = Producto.objects.count()
    productos_criticos = Producto.objects.filter(stock_actual__lte=10, activo=True)
    conteo_criticos = productos_criticos.count()
 
    # 5. RENDIMIENTO Y CARGA LABORAL (Doctores Hoy)
    doctores_hoy = Cita.objects.filter(fecha_hora__date=hoy) \
        .values('id_doctor__id_usuario__nombre', 'id_doctor__id_usuario__apellidos') \
        .annotate(total=Count('id_cita')).order_by('-total')
 
    # FIX: evita división por cero en el template si no hay citas hoy
    max_citas_doctor = max([d['total'] for d in doctores_hoy]) if doctores_hoy else 1
    if max_citas_doctor == 0:
        max_citas_doctor = 1
 
    # 6. DATOS PARA RENDIMIENTO SEMANAL (Gráfica de barras) — FIX REAL
    # El original contaba TODAS las citas realizadas/canceladas de la historia
    # completa y repetía ese único número 6 veces (gráfica plana, sin sentido).
    # Aquí agrupamos de verdad por día, dentro de la semana calendario actual
    # (lunes a sábado).
    lunes_semana = hoy - datetime.timedelta(days=hoy.weekday())  # weekday(): lunes=0
    dias_semana = [lunes_semana + datetime.timedelta(days=i) for i in range(6)]  # Lun..Sáb
    labels_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
 
    citas_semana_qs = Cita.objects.filter(fecha_hora__date__gte=dias_semana[0], fecha_hora__date__lte=dias_semana[-1])
 
    realizadas_por_dia = citas_semana_qs.filter(id_estado_cita__nombre_estado__icontains='realizada') \
        .annotate(dia=TruncDate('fecha_hora')).values('dia').annotate(total=Count('id_cita'))
    canceladas_por_dia = citas_semana_qs.filter(id_estado_cita__nombre_estado__icontains='cancelada') \
        .annotate(dia=TruncDate('fecha_hora')).values('dia').annotate(total=Count('id_cita'))
 
    realizadas_map = {r['dia']: r['total'] for r in realizadas_por_dia}
    canceladas_map = {c['dia']: c['total'] for c in canceladas_por_dia}
 
    realizadas_sem = [realizadas_map.get(d, 0) for d in dias_semana]
    canceladas_sem = [canceladas_map.get(d, 0) for d in dias_semana]
 
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
 
    # 8. NUEVO: PAGOS PENDIENTES MÁS URGENTES (accionable, no solo un número)
    # Usa la property real del modelo (costo_final - total_abonado) en vez del
    # estado textual de la cita, así que sí refleja saldo pendiente real.
    citas_con_saldo_candidatas = Cita.objects.filter(fecha_hora__date__lte=hoy) \
        .select_related('id_paciente__id_usuario', 'id_doctor__id_usuario') \
        .order_by('-fecha_hora')[:50]  # ventana razonable; ajustar si el volumen crece
 
    pagos_pendientes_top = []
    for c in citas_con_saldo_candidatas:
        saldo = c.saldo_pendiente
        if saldo and saldo > 0:
            pagos_pendientes_top.append(c)
        if len(pagos_pendientes_top) >= 5:
            break
 
    # 10. NUEVO: TOP PRODUCTOS MÁS CONSUMIDOS (mes actual)
    # Se basa en MovimientoInventario con tipo_movimiento='SALIDA', que es el
    # registro real de consumo (no el stock_actual, que solo muestra el nivel
    # presente y no dice qué se ha estado gastando).
    top_productos_consumidos = MovimientoInventario.objects.filter(
        tipo_movimiento='SALIDA',
        fecha_movimiento__month=mes_actual,
        fecha_movimiento__year=anio_actual,
    ).values('id_producto__nombre_producto').annotate(
        total_consumido=Sum('cantidad')
    ).order_by('-total_consumido')[:10]
 
    top_productos_labels = [p['id_producto__nombre_producto'] for p in top_productos_consumidos]
    top_productos_data = [p['total_consumido'] for p in top_productos_consumidos]
 
    # 11. NUEVO: MAPA DE CALOR DE HORAS PICO (mes actual)
    # Matriz día de semana (Lun-Dom) x hora (7am-8pm, horario clínico típico).
    # Se arma como lista de [dia_idx, hora_idx, conteo] para graficar con un
    # heatmap manual en Chart.js (sin dependencias extra).
    HORAS_CLINICA = list(range(7, 21))  # 7:00 a 20:00
    DIAS_LABELS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
 
    citas_mes_qs = Cita.objects.filter(fecha_hora__month=mes_actual, fecha_hora__year=anio_actual)
 
    citas_por_hora_dia = citas_mes_qs.annotate(
        hora=ExtractHour('fecha_hora'),
        # ExtractWeekDay en Django: domingo=1 ... sábado=7. Convertimos a Lun=0..Dom=6.
        dow_django=ExtractWeekDay('fecha_hora'),
    ).values('hora', 'dow_django').annotate(total=Count('id_cita'))
 
    # Mapa: (dia_idx Lun=0..Dom=6, hora) -> total
    heatmap_map = {}
    max_heat = 0
    for row in citas_por_hora_dia:
        dow_django = row['dow_django']  # 1=Dom..7=Sáb
        dia_idx = (dow_django - 2) % 7  # convierte a Lun=0..Dom=6
        hora = row['hora']
        if hora in HORAS_CLINICA:
            heatmap_map[(dia_idx, hora)] = row['total']
            if row['total'] > max_heat:
                max_heat = row['total']
 
    heatmap_data = []
    for dia_idx in range(7):
        for hora in HORAS_CLINICA:
            heatmap_data.append({
                'dia': dia_idx,
                'hora': hora,
                'total': heatmap_map.get((dia_idx, hora), 0),
            })
 
    # 9. PRÓXIMAS CITAS Y LOGS GLOBALES
    citas_proximas = Cita.objects.filter(fecha_hora__date=hoy).select_related(
        'id_paciente__id_usuario', 'id_doctor__id_usuario', 'id_estado_cita'
    ).order_by('fecha_hora')[:5]
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
        'pagos_pendientes_top': pagos_pendientes_top,
 
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
 
        'top_productos_labels': top_productos_labels,
        'top_productos_data': top_productos_data,
 
        'heatmap_data': heatmap_data,
        'heatmap_dias_labels': DIAS_LABELS,
        'heatmap_horas': HORAS_CLINICA,
        'heatmap_max': max_heat if max_heat > 0 else 1,
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
                nuevo_usuario = form.save(commit=False)
                rol = nuevo_usuario.id_rol.nombre_rol.lower()

                # =========================================================
                # PASO 1: CONSTRUIR PERFIL EN MEMORIA SIN TOCAR LA BD
                # =========================================================
                perfil = None

                if 'doctor' in rol or 'medico' in rol:
                    especialidad = request.POST.get('id_especialidad', '').strip()
                    licencia     = request.POST.get('licencia_medica', '').strip()
                    if not especialidad:
                        raise Exception("Debe seleccionar una especialidad.")
                    if not licencia:
                        raise Exception("La licencia médica es obligatoria.")
                    perfil = Medico(
                        id_especialidad_id=especialidad,
                        licencia_medica=licencia,
                        anos_experiencia=request.POST.get('anos_experiencia') or None,
                        fecha_ingreso=request.POST.get('fecha_ingreso') or None
                    )

                elif 'secretaria' in rol:
                    turno = request.POST.get('turno', '').strip()
                    if not turno:
                        raise Exception("Debe seleccionar un turno.")
                    perfil = Secretaria(
                        fecha_ingreso=request.POST.get('fecha_ingreso') or None,
                        turno=turno
                    )

                elif 'paciente' in rol:
                    fecha_nac = request.POST.get('fecha_nacimiento', '').strip()
                    tel_emer  = request.POST.get('contacto_emergencia_telefono', '').strip()
                    if not fecha_nac:
                        raise Exception("La fecha de nacimiento es obligatoria.")
                    if not tel_emer:
                        raise Exception("El teléfono de emergencia es obligatorio.")
                    perfil = Paciente(
                        fecha_nacimiento=fecha_nac,
                        direccion=request.POST.get('direccion'),
                        eps=request.POST.get('eps'),
                        rh=request.POST.get('rh'),
                        alergias=request.POST.get('alergias'),
                        enfermedades_preexistentes=request.POST.get('enfermedades_preexistentes'),
                        contacto_emergencia_nombre=request.POST.get('contacto_emergencia_nombre'),
                        contacto_emergencia_telefono=tel_emer
                    )

                # =========================================================
                # PASO 2: GUARDAR — DESCONECTANDO EL SIGNAL TEMPORALMENTE
                # Evita que el signal cree un perfil vacío antes que nosotros
                # =========================================================
                from django.db.models.signals import post_save
                from CuentasApp.signals import crear_perfil_usuario

                with transaction.atomic():
                    # Desconectar signal solo durante este bloque
                    post_save.disconnect(crear_perfil_usuario, sender=Usuario)
                    try:
                        nuevo_usuario.set_password(form.cleaned_data['password'])
                        nuevo_usuario.save()

                        if perfil is not None:
                            perfil.id_usuario = nuevo_usuario
                            perfil.save()
                    finally:
                        # Reconectar SIEMPRE, aunque haya error
                        post_save.connect(crear_perfil_usuario, sender=Usuario)

                messages.success(
                    request,
                    f"✅ Usuario '{nuevo_usuario.nombre_usuario}' guardado correctamente."
                )
                return redirect('admin_app:lista_usuarios')

            except Exception as e:
                messages.error(request, f"❌ Error: {e}")

        else:
            messages.error(request, "⚠ Corrige los errores del formulario.")

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
