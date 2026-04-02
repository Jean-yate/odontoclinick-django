from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class UsuarioManager(BaseUserManager):
    def create_user(self, nombre_usuario, correo, password=None, **extra_fields):
        if not correo:
            raise ValueError('El usuario debe tener un correo electrónico')
        
        user = self.model(
            nombre_usuario=nombre_usuario,
            correo=self.normalize_email(correo),
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    # Dejamos esto simple por si decides usarlo después, 
    # pero ahora el control es por el campo 'id_rol'
    def create_superuser(self, nombre_usuario, correo, password=None, **extra_fields):
        return self.create_user(nombre_usuario, correo, password, **extra_fields)

class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre_rol = models.CharField(unique=True, max_length=50)
    descripcion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rol'

    def __str__(self):
        return self.nombre_rol

class Estado(models.Model):
    id_estado = models.AutoField(primary_key=True)
    nombre_estado = models.CharField(unique=True, max_length=20)

    class Meta:
        managed = False
        db_table = 'estado'

    def __str__(self):
        return self.nombre_estado

class Usuario(AbstractBaseUser):
    id_usuario = models.AutoField(primary_key=True)
    nombre_usuario = models.CharField(unique=True, max_length=50)
    nombre = models.CharField(max_length=50)
    apellidos = models.CharField(max_length=100)
    correo = models.EmailField(unique=True, max_length=100)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    
    password = models.CharField(max_length=255, db_column='contrasena')
    
    id_rol = models.ForeignKey(Rol, models.DO_NOTHING, db_column='id_rol')
    id_estado = models.ForeignKey(Estado, models.DO_NOTHING, db_column='id_estado')
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(blank=True, null=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'nombre_usuario'
    REQUIRED_FIELDS = ['correo']

    class Meta:
        managed = False
        db_table = 'usuario'

    # --- LÓGICA DE PERMISOS UNIFICADA ---
    @property
    def is_staff(self):
        # Si el rol en MariaDB es Administrador, tiene permiso de staff
        return self.id_rol.nombre_rol == 'Administrador'

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return self.is_staff
    
    @property
    def is_superuser(self):
        # El Administrador también es Superusuario
        return self.id_rol.nombre_rol == 'Administrador'
    # ------------------------------------

    def __str__(self):
        return f"{self.nombre} {self.apellidos} ({self.nombre_usuario})"
    
    def save(self, *args, **kwargs):
        # Si la contraseña no está encriptada (no empieza con el algoritmo de Django)
        if self.password and not self.password.startswith('pbkdf2_'):
            self.set_password(self.password)
        super().save(*args, **kwargs)
    
class Secretaria(models.Model):
    id_secretaria = models.AutoField(primary_key=True)
    id_usuario = models.OneToOneField('Usuario', models.DO_NOTHING, db_column='id_usuario')
    fecha_ingreso = models.DateField(blank=True, null=True)
    turno = models.CharField(max_length=8, blank=True, null=True)

    class Meta:
        managed = False # IMPORTANTE: Déjalo en False para que Django no intente borrarla de MariaDB
        db_table = 'secretaria'

    def __str__(self):
        return f"Secretaria: {self.id_usuario.nombre}"