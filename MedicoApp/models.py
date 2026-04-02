from django.db import models

class Especialidad(models.Model):
    id_especialidad = models.AutoField(primary_key=True)
    nombre_especialidad = models.CharField(unique=True, max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'especialidad'

class Medico(models.Model):
    id_doctor = models.AutoField(primary_key=True)
    id_usuario = models.OneToOneField('CuentasApp.Usuario', models.DO_NOTHING, db_column='id_usuario')
    id_especialidad = models.ForeignKey(Especialidad, models.DO_NOTHING, db_column='id_especialidad')
    licencia_medica = models.CharField(max_length=50, blank=True, null=True)
    anos_experiencia = models.IntegerField(blank=True, null=True)
    fecha_ingreso = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'medico'

    def __str__(self):
        return f"Dr. {self.id_usuario.nombre} {self.id_usuario.apellidos}"

class Horario(models.Model):
    id_horario = models.AutoField(primary_key=True)
    id_doctor = models.ForeignKey('Medico', models.DO_NOTHING, db_column='id_doctor')
    dia_semana = models.CharField(max_length=9)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    duracion_cita_minutos = models.IntegerField()
    activo = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'horario'


