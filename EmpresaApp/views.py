from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
import openpyxl
import json

from .models import Empresa
from .forms import EmpresaForm
from InventarioApp.views import es_auxiliar_o_admin


@login_required
@user_passes_test(es_auxiliar_o_admin)
def lista_empresas(request):
    empresas = Empresa.objects.all().order_by('nombre_empresa')
    nombre_q   = request.GET.get('nombre', '').strip()
    tipo_filtro = request.GET.get('tipo', '')

    if nombre_q:
        empresas = empresas.filter(
            Q(nombre_empresa__icontains=nombre_q) | Q(nit__icontains=nombre_q)
        )
    if tipo_filtro == 'proveedor':
        empresas = empresas.filter(es_proveedor=True)
    elif tipo_filtro == 'comprador':
        empresas = empresas.filter(es_comprador=True)

    if request.GET.get('exportar') == 'excel':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Empresas"
        ws.append(['ID', 'Nombre', 'NIT', 'Proveedor', 'Comprador'])
        for e in empresas:
            ws.append([
                e.id_empresa, e.nombre_empresa, e.nit,
                'Sí' if e.es_proveedor else 'No',
                'Sí' if e.es_comprador else 'No',
            ])
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Empresas.xlsx"'
        wb.save(response)
        return response

    return render(request, 'EmpresaApp/lista_empresas.html', {
        'empresas': empresas,
        'total': empresas.count(),
        'form': EmpresaForm(),
    })


@login_required
@user_passes_test(es_auxiliar_o_admin)
def crear_empresa(request):
    if request.method == 'POST':
        form = EmpresaForm(request.POST)
        if form.is_valid():
            empresa = form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'ok',
                    'id': empresa.id_empresa,
                    'nombre': empresa.nombre_empresa,
                    'nit': empresa.nit,
                    'es_proveedor': empresa.es_proveedor,
                    'es_comprador': empresa.es_comprador,
                })
            messages.success(request, f"Empresa '{empresa.nombre_empresa}' creada exitosamente.")
            return redirect('EmpresaApp:lista_empresas')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    return redirect('EmpresaApp:lista_empresas')


@login_required
@user_passes_test(es_auxiliar_o_admin)
def editar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=empresa)
        if form.is_valid():
            empresa = form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'ok',
                    'nombre': empresa.nombre_empresa,
                    'nit': empresa.nit,
                    'es_proveedor': empresa.es_proveedor,
                    'es_comprador': empresa.es_comprador,
                })
            messages.success(request, f"Empresa '{empresa.nombre_empresa}' actualizada.")
            return redirect('EmpresaApp:lista_empresas')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    else:
        # GET: devuelve datos para pre-rellenar el modal (no se usa en la nueva versión,
        # pero se mantiene por compatibilidad)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'id': empresa.id_empresa,
                'nombre_empresa': empresa.nombre_empresa,
                'nit': empresa.nit,
                'es_proveedor': empresa.es_proveedor,
                'es_comprador': empresa.es_comprador,
            })
    return redirect('EmpresaApp:lista_empresas')


@login_required
@user_passes_test(es_auxiliar_o_admin)
def alternar_tipo_empresa(request, pk):
    if request.method == 'POST':
        empresa = get_object_or_404(Empresa, pk=pk)
        try:
            data  = json.loads(request.body)
            campo = data.get('campo')
            if campo in ('es_proveedor', 'es_comprador'):
                setattr(empresa, campo, not getattr(empresa, campo))
                empresa.save()
                return JsonResponse({'status': 'ok', 'valor': getattr(empresa, campo)})
        except (json.JSONDecodeError, Exception):
            pass
    return JsonResponse({'status': 'error'}, status=400)