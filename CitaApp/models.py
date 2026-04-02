from django.db import models

class EstadoCita(models.Model):
    id_estado_cita = models.AutoField(primary_key=True)
    nombre_estado = models.CharField(unique=True, max_length=50)
    color = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'estado_cita'

    def __str__(self):
        return self.nombre_estado

class Cita(models.Model):
    id_cita = models.AutoField(primary_key=True)
    id_paciente = models.ForeignKey('PacienteApp.Paciente', models.DO_NOTHING, db_column='id_paciente')
    id_doctor = models.ForeignKey('MedicoApp.Medico', models.DO_NOTHING, db_column='id_doctor')
    fecha_hora = models.DateTimeField()
    id_estado_cita = models.ForeignKey('EstadoCita', models.DO_NOTHING, db_column='id_estado_cita')
    notas_paciente = models.TextField(blank=True, null=True)
    notas_doctor = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField()
    fecha_actualizacion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'cita'

class CitaTratamiento(models.Model):
    id_cita_tratamiento = models.AutoField(primary_key=True)
    id_cita = models.ForeignKey(Cita, models.DO_NOTHING, db_column='id_cita')
    id_tratamiento = models.ForeignKey('TratamientoApp.Tratamiento', models.DO_NOTHING, db_column='id_tratamiento')
    costo_aplicado = models.DecimalField(max_digits=10, decimal_places=2)
    observaciones = models.TextField(blank=True, null=True)
    completado = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cita_tratamiento'
        unique_together = (('id_cita', 'id_tratamiento'),)

