from django.db import models

class Paciente(models.Model):
    id_paciente = models.AutoField(primary_key=True)
    id_usuario = models.OneToOneField('CuentasApp.Usuario', models.DO_NOTHING, db_column='id_usuario')
    fecha_nacimiento = models.DateField(blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    eps = models.CharField(max_length=100, blank=True, null=True)
    rh = models.CharField(max_length=5, blank=True, null=True)
    alergias = models.TextField(blank=True, null=True)
    enfermedades_preexistentes = models.TextField(blank=True, null=True)
    contacto_emergencia_nombre = models.CharField(max_length=100, blank=True, null=True)
    contacto_emergencia_telefono = models.CharField(max_length=15, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = True
        db_table = 'paciente'

    def __str__(self):
        return f"{self.id_usuario.nombre} {self.id_usuario.apellidos}"

class HistorialMedico(models.Model):
    id_historial = models.AutoField(primary_key=True)
    id_paciente = models.ForeignKey('Paciente', models.DO_NOTHING, db_column='id_paciente')
    id_cita = models.ForeignKey('CitaApp.Cita', models.DO_NOTHING, db_column='id_cita', blank=True, null=True)
    id_doctor = models.ForeignKey('MedicoApp.Medico', models.DO_NOTHING, db_column='id_doctor')
    fecha = models.DateField()
    diagnostico = models.TextField()
    tratamiento_realizado = models.TextField()
    observaciones = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'historial_medico'