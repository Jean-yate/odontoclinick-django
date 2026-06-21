from django.db import migrations

def crear_estados_iniciales(apps, schema_editor):
    # Recuperamos el modelo exacto según tu Meta db_table y clase
    EstadoCita = apps.get_model('CitaApp', 'EstadoCita')
    
    # Creamos el estado crítico para tu flujo del QR y del monitor de sala
    # Le asignamos un color amarillo/naranja estándar de Bootstrap (#ffc107) para su badge
    EstadoCita.objects.get_or_create(
        nombre_estado='En Espera',
        defaults={'color': '#ffc107'}
    )

def eliminar_estados_iniciales(apps, schema_editor):
    EstadoCita = apps.get_model('CitaApp', 'EstadoCita')
    # Lógica inversa en caso de revertir la migración
    EstadoCita.objects.filter(nombre_estado='En Espera').delete()

class Migration(migrations.Migration):

    dependencies = [
        # REVISA AQUÍ: Debe apuntar al nombre de tu archivo de migración anterior (normalmente '0001_initial')
        ('CitaApp', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_estados_iniciales, eliminar_estados_iniciales),
    ]