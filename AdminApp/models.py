from django.db import models
from django.conf import settings


class Auditoria(models.Model):
    """
    Bitácora de acciones críticas del sistema: quién hizo qué, cuándo y
    desde dónde. Se alimenta manualmente desde las vistas que realizan
    operaciones sensibles (crear/editar/eliminar usuarios, roles,
    catálogos, login/logout), no automáticamente para cada petición —
    así los registros son legibles y describen acciones reales, no
    rutas HTTP crudas.
    """
    id_auditoria = models.AutoField(primary_key=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_usuario',
        help_text="Usuario que realizó la acción. Null si fue un visitante anónimo (ej. intento de login fallido).",
    )
    accion = models.CharField(
        max_length=100,
        help_text="Descripción corta de la acción, ej. 'Inicio de sesión', 'Crear usuario', 'Eliminar rol'.",
    )
    detalles = models.TextField(
        blank=True,
        null=True,
        help_text="Contexto adicional legible, ej. 'Usuario admin_total creó el doctor Juan Pérez'.",
    )
    ip_direccion = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP real del cliente (ya resuelta detrás del proxy de Railway).",
    )

    class Meta:
        managed = True
        db_table = 'auditoria'
        ordering = ['-fecha_hora']
        verbose_name_plural = "Auditorías"

    def __str__(self):
        return f"{self.fecha_hora:%Y-%m-%d %H:%M} · {self.accion}"
