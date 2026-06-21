# Esta migración originalmente agregaba el campo id_cita a MovimientoInventario,
# asumiendo que 0001_initial no lo incluía todavía.
#
# FIX: en el código actual, InventarioApp.0001_initial YA incluye el campo
# id_cita en MovimientoInventario (línea ~78 de ese archivo). Esta migración
# solo tenía sentido para bases de datos viejas creadas ANTES de que
# 0001_initial se corrigiera para incluir el campo. En una base de datos
# nueva (como Railway), correr el AddField original choca con
# "Duplicate column name 'id_cita'", porque la columna ya existe.
#
# La convertimos en SeparateDatabaseAndState: el estado de Django se
# actualiza igual (mantiene compatibilidad con bases viejas que ya tenían
# esta migración aplicada en su django_migrations), pero no se ejecuta
# SQL real, porque la columna ya existe desde 0001_initial.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('InventarioApp', '0002_productoempresa'),
        ('CitaApp', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
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
            ],
            database_operations=[],  # sin SQL real: la columna id_cita ya existe, creada por InventarioApp.0001_initial
        ),
    ]