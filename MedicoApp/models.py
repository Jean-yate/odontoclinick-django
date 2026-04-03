from django.db import models

class Especialidad(models.Model):
    id_especialidad = models.AutoField(primary_key=True)
    nombre_especialidad = models.CharField(unique=True, max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'especialidad'

class Medico(models.Model):
    id_doctor = models.AutoField(primary_key=True)
    id_usuario = models.OneToOneField('CuentasApp.Usuario', models.DO_NOTHING, db_column='id_usuario')
    id_especialidad = models.ForeignKey(Especialidad, models.DO_NOTHING, db_column='id_especialidad')
    licencia_medica = models.CharField(max_length=50, blank=True, null=True)
    anos_experiencia = models.IntegerField(blank=True, null=True)
    fecha_ingreso = models.DateField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'medico'

    def __str__(self):
        return f"Dr. {self.id_usuario.nombre} {self.id_usuario.apellidos}"

# class Horario(models.Model):
#     id_horario = models.AutoField(primary_key=True)
#     id_doctor = models.ForeignKey('Medico', models.DO_NOTHING, db_column='id_doctor')
#     dia_semana = models.CharField(max_length=9)
#     hora_inicio = models.TimeField()
#     hora_fin = models.TimeField()
#     duracion_cita_minutos = models.IntegerField()
#     activo = models.IntegerField(blank=True, null=True)

class Disponibilidad(models.Model):
    id_disponibilidad = models.AutoField(primary_key=True)
    dias = [
        (1, 'Lunes'), (2, 'Martes'), (3, 'Miércoles'),
        (4, 'Jueves'), (5, 'Viernes'), (6, 'Sábado'),
        (7, 'Domingo'),
    ]
    id_medico = models.ForeignKey('Medico', on_delete=models.CASCADE, db_column='id_medico')
    dia_semana = models.IntegerField(choices=dias)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    duracion_cita = models.IntegerField(default=30)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'disponibilidad'
        verbose_name_plural = "Disponibilidades"

class HistorialMedico(models.Model):
    id_historial = models.AutoField(primary_key=True)
    
    # La conexión única con la gestión de la cita
    id_cita = models.OneToOneField(
        'CitaApp.Cita', 
        on_delete=models.CASCADE, 
        db_column='id_cita',
        related_name='historial'
    )
    
    # ¿Qué se hizo?
    id_tratamiento = models.ForeignKey(
        'TratamientoApp.Tratamiento', 
        on_delete=models.PROTECT, # Protegemos para no borrar tratamientos con historial
        db_column='id_tratamiento'
    )
    
    # --- AQUÍ MOVEMOS LO DE CITA_TRATAMIENTO ---
    costo_aplicado = models.DecimalField(max_digits=10, decimal_places=2)
    completado = models.BooleanField(default=True)
    
    # --- INFORMACIÓN CLÍNICA ---
    diagnostico = models.TextField()
    observaciones_clinicas = models.TextField(blank=True, null=True)
    
    # Notas que venían de la cita
    notas_paciente = models.TextField(blank=True, null=True)
    notas_doctor = models.TextField(blank=True, null=True)
    sintomas = models.TextField(blank=True, null=True)
    plan_tratamiento = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'historial_medico'
