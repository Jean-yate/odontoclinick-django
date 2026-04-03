from django.db import models

class MetodoPago(models.Model):
    id_metodo_pago = models.AutoField(primary_key=True)
    nombre_metodo = models.CharField(unique=True, max_length=50)
    activo = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'metodo_pago'

class Pago(models.Model):
    id_pago = models.AutoField(primary_key=True)
    id_cita = models.ForeignKey('CitaApp.Cita', models.DO_NOTHING, db_column='id_cita')
    fecha_pago = models.DateTimeField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    id_metodo_pago = models.ForeignKey(MetodoPago, models.DO_NOTHING, db_column='id_metodo_pago')
    referencia = models.CharField(max_length=100, blank=True, null=True)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'pago'


