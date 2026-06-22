from django.db import migrations
from django.conf import settings

def actualizar_site(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    Site.objects.update_or_create(
        id=1,
        defaults={
            'domain': config('SITE_DOMAIN', default='localhost:8000'),
            'name': 'OdontoClinick',
        }
    )

from decouple import config

class Migration(migrations.Migration):

    dependencies = [
        ('CuentasApp', '000X_tu_migracion_anterior'),  # ajusta este número
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(actualizar_site, migrations.RunPython.noop),
    ]