from django.db import models

class Tratamiento(models.Model):
    id_tratamiento = models.AutoField(primary_key=True)
    codigo = models.CharField(unique=True, max_length=20, blank=True, null=True)
    nombre_tratamiento = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    costo_base = models.DecimalField(max_digits=10, decimal_places=2)
    duracion_estimada_minutos = models.IntegerField(blank=True, null=True)
    activo = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'tratamiento'

class TratamientoProducto(models.Model):
    id_tratamiento_producto = models.AutoField(primary_key=True)
    id_tratamiento = models.ForeignKey(Tratamiento, models.DO_NOTHING, db_column='id_tratamiento')
    id_producto = models.ForeignKey('InventarioApp.Producto', models.DO_NOTHING, db_column='id_producto')
    cantidad_requerida = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = True
        db_table = 'tratamiento_producto'
        unique_together = (('id_tratamiento', 'id_producto'),)


