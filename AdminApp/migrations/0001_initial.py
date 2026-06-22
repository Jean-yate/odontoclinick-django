# Generated manually para el modelo Auditoria (bitácora del sistema)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Auditoria',
            fields=[
                ('id_auditoria', models.AutoField(primary_key=True, serialize=False)),
                ('fecha_hora', models.DateTimeField(auto_now_add=True)),
                ('accion', models.CharField(help_text="Descripción corta de la acción, ej. 'Inicio de sesión', 'Crear usuario', 'Eliminar rol'.", max_length=100)),
                ('detalles', models.TextField(blank=True, help_text="Contexto adicional legible, ej. 'Usuario admin_total creó el doctor Juan Pérez'.", null=True)),
                ('ip_direccion', models.GenericIPAddressField(blank=True, help_text='IP real del cliente (ya resuelta detrás del proxy de Railway).', null=True)),
                ('id_usuario', models.ForeignKey(blank=True, db_column='id_usuario', help_text='Usuario que realizó la acción. Null si fue un visitante anónimo (ej. intento de login fallido).', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'auditoria',
                'verbose_name_plural': 'Auditorías',
                'ordering': ['-fecha_hora'],
            },
        ),
    ]
