"""
Utilidad central para registrar eventos en la bitácora de auditoría.

Se llama manualmente desde las vistas que realizan acciones críticas
(crear/editar/eliminar usuarios, roles, catálogos, login/logout), en vez
de interceptar automáticamente cada petición — así los registros son
legibles y describen acciones reales del negocio.
"""
from .models import Auditoria


def obtener_ip_cliente(request):
    """
    Devuelve la IP real del visitante.

    Railway (como la mayoría de plataformas con proxy/load balancer)
    coloca la app detrás de un proxy interno. Sin esto, request.META
    ['REMOTE_ADDR'] devolvería la IP del proxy de Railway, no la del
    visitante real. El header X-Forwarded-For contiene la cadena de IPs
    que la petición atravesó; la primera es la del cliente original.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Puede venir como "ip_cliente, ip_proxy1, ip_proxy2" — tomamos la primera
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def registrar_auditoria(request, accion, detalles=None):
    """
    Crea un registro en la bitácora de auditoría.

    Uso típico desde una vista:
        registrar_auditoria(request, "Crear usuario", f"Se creó el usuario '{nuevo_usuario.nombre_usuario}'")

    Si request.user no está autenticado (ej. un intento de login fallido),
    se guarda igual con id_usuario=None.
    """
    usuario = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    try:
        Auditoria.objects.create(
            id_usuario=usuario,
            accion=accion,
            detalles=detalles,
            ip_direccion=obtener_ip_cliente(request),
        )
    except Exception as e:
        # La auditoría nunca debe romper el flujo principal de la app:
        # si falla el registro (ej. problema temporal de BD), solo se
        # imprime en logs, no se propaga la excepción.
        print(f"[ERROR AUDITORIA]: {e}")
