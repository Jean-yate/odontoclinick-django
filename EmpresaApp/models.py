from django.db import models

class Empresa(models.Model):
    id_empresa = models.AutoField(primary_key=True)
    nombre_empresa = models.CharField(max_length=255, unique=True, verbose_name="Nombre de la Empresa")
    nit = models.CharField(max_length=50, unique=True, verbose_name="NIT")
    es_proveedor = models.BooleanField(default=True, verbose_name="¿Es Proveedor?")
    es_comprador = models.BooleanField(default=False, verbose_name="¿Es Comprador?")

    def __str__(self):
        return self.nombre_empresa

    class Meta:
        managed = True
        db_table = 'empresa'