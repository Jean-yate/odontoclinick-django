# Generated manually — agrega el FK id_cita que quedó fuera de 0001_initial
# porque CitaApp.Cita no estaba disponible en ese momento o hubo un error de orden.
#
# INSTRUCCIONES:
#   1. Guarda este archivo como:
#      InventarioApp/migrations/0003_movimientoinventario_id_cita.py
#   2. Ejecuta:  python manage.py migrate InventarioApp
#
# Si ya existe una migración 0003, cambia el nombre a 0004 y ajusta dependencies.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # Ajusta '0002_...' al nombre real de tu última migración en InventarioApp
        ('InventarioApp', '0002_productoempresa'),
        # CitaApp debe estar migrado antes que este
        ('CitaApp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='movimientoinventario',
            name='id_cita',
            field=models.ForeignKey(
                blank=True,
                db_column='id_cita',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='insumos_consumidos',
                to='CitaApp.cita',
            ),
        ),
    ]