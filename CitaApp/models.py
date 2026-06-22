from django.db import models
from django.db.models import Sum
from django.conf import settings
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
from CuentasApp.models import Usuario

class EstadoCita(models.Model):
    id_estado_cita = models.AutoField(primary_key=True)
    nombre_estado = models.CharField(max_length=50) # Ej: Programada, En Espera, Atendida
    color = models.CharField(max_length=20, default='#6c757d') # Para los badges

    def __str__(self):
        return self.nombre_estado
    
    class Meta:
        db_table = 'estado_cita'

class Cita(models.Model):
    id_cita = models.AutoField(primary_key=True)
    id_paciente = models.ForeignKey('PacienteApp.Paciente', on_delete=models.CASCADE)
    id_doctor = models.ForeignKey('MedicoApp.Medico', on_delete=models.CASCADE)
    id_estado_cita = models.ForeignKey(EstadoCita, on_delete=models.SET_NULL, null=True)
    fecha_hora = models.DateTimeField()
    motivo = models.TextField(blank=True, null=True)
    monto_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=0)   
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    qr_code = models.ImageField(
        upload_to='qrcodes/',
        blank=True,
        null=True
    )
    hora_llegada = models.DateTimeField(
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.qr_code:
            # FIX: antes esto tenía 'http://127.0.0.1:8000' hardcodeado, lo
            # que hacía que CUALQUIER QR generado en producción apuntara a
            # localhost — inútil al escanearlo desde un celular real. Ahora
            # usa settings.SITE_URL, que se configura por entorno (variable
            # de entorno SITE_URL): localhost en desarrollo, el dominio real
            # de Railway en producción.
            qr_data = f"{settings.SITE_URL}/citas/checkin/{self.id_cita}/"

            qr = qrcode.make(qr_data)

            buffer = BytesIO()
            qr.save(buffer, format='PNG')
            buffer.seek(0)

            filename = f'cita_{self.id_cita}.png'

            self.qr_code.save(
                filename,
                File(buffer),
                save=False
            )

            super().save(update_fields=['qr_code'])

    class Meta:
        db_table = 'cita'
        unique_together = ('id_doctor', 'fecha_hora')
    
    def __str__(self):
        return f"{self.id_paciente} - {self.fecha_hora}"

    # --- PROPIEDADES INTELIGENTES (LÓGICA MATEMÁTICA) ---
    @property
    def costo_final(self):
        if hasattr(self, 'historial') and self.historial.costo_aplicado > 0:
            return self.historial.costo_aplicado
        return self.monto_estimado or 0

    @property
    def total_abonado(self):
        from FacturacionApp.models import Pago
        total = Pago.objects.filter(id_cita=self).aggregate(total=models.Sum('monto'))['total']
        return total or 0
    
    @property
    def saldo_pendiente(self):
        return self.costo_final - self.total_abonado

    @property
    def estado_pago(self):
        """Retorna un diccionario con el estado visual para el template."""
        abonado = self.total_abonado
        total = self.costo_final

        if total == 0:
            return {'texto': 'Sin Monto', 'color': 'secondary'}
        if abonado == 0:
            return {'texto': 'No Pagado', 'color': 'danger'}
        if abonado < total:
            return {'texto': f'Abono: ${abonado}', 'color': 'warning'}
        return {'texto': 'Pagado', 'color': 'success'}