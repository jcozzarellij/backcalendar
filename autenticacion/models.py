from django.core.validators import FileExtensionValidator
from django.db import models
from core.custom_models import ModeloBase
from core.funciones_adicionales import remover_espacios_de_mas
from core.models_utils import FileNameUploadToPath
from core.validadores import solo_numeros, validate_file_size_2mb
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as trad


class Usuario(AbstractUser, ModeloBase):
    TIPO_DOCUMENTO = (
        ("C", "Cédula"),
        ("R", "RUC"),
        ("P", "Pasaporte"),
        ("N", "Ninguno"),
    )
    SEXO = (
        ("MASCULINO", "Masculino"),
        ("FEMENINO", "Femenino"),
        ("NINGUNO", "Sin definir"),
    )
    email = models.EmailField(trad('email address'), unique=False)
    # SEGURIDAD (XSS almacenado): NO permitir 'svg' — un inquilino podía subir un SVG con
    # <script> como foto y, servido same-origin desde /media/, ejecutar JS (robo de CSRF).
    foto = models.FileField(upload_to=FileNameUploadToPath('fotousuario/', "foto_perfil", ["username"]), max_length=600, blank=True, null=True, verbose_name="Foto", validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'tiff', "jfif"]), validate_file_size_2mb])
    sexo = models.CharField(verbose_name="Sexo", max_length=50, choices=SEXO, null=True, blank=True)
    fecha_nacimiento = models.DateField("Fecha de nacimiento", null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True, verbose_name='Teléfonos', validators=[solo_numeros])
    tipo_documento = models.CharField(verbose_name="Tipo Documento", max_length=50, choices=TIPO_DOCUMENTO, default="N")
    documento = models.CharField(max_length=20, null=True, blank=True, verbose_name='Cédula/RUC/Pasaporte', validators=[solo_numeros])
    ciudad = models.ForeignKey('area_geografica.Ciudad', on_delete=models.PROTECT, blank=True, null=True, verbose_name='Ciudad')
    direccion = models.TextField(verbose_name='Dirección')
    cambio_clave = models.BooleanField(default=False, verbose_name='Cambio de Contraseña Obligatorio')
    # CONFIGURACIÓN DE USUARIO
    notificar_por_correo = models.BooleanField(default=True, verbose_name='Recibe notificaciones por correo')
    # TIPO_DOCUMENTO
    CEDULA = "C"
    RUC = "R"
    PASAPORTE = "P"

    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name).title()

    def groups_str(self):
        return ", ".join(list(self.groups.all().values_list('name', flat=True)))

    def nombre_corto(self):
        import re
        fn = re.sub("\s+", " ", self.first_name.strip()).split(" ")
        ln = re.sub("\s+", " ", self.last_name.strip()).split(" ")
        return "{} {}".format(fn[0], ln[0]).title()

    def get_foto(self):
        if self.foto:
            return self.foto.url
        else:
            return "/static/foto_defaultd.png"

    def get_foto_gris(self):
        try:
            if self.foto == '':
                inicial = self.first_name[0]
                if inicial and not inicial.isdigit():
                    return f"/static/images/initials/gris/{inicial}.png"
                return "/static/foto_defaultd.png"
            return self.foto.url
        except Exception:
            return "/static/foto_defaultd.png"

    def datos(self):
        return "{} {}".format(self.first_name, self.last_name).title()

    def save(self, *args, **kwargs):
        self.first_name = remover_espacios_de_mas(self.first_name).title()
        self.last_name = remover_espacios_de_mas(self.last_name).title()
        super(Usuario, self).save(*args, **kwargs)

    def es_administrativo(self):
        """Único perfil de la plataforma: usuario activo con acceso al panel (staff o superusuario).
        El alcance lo definen sus grupos (roles)."""
        return bool(self.is_active and self.status and (self.is_staff or self.is_superuser))

    def __str__(self):
        return "{} {} {}".format(self.documento, self.last_name, self.first_name).title()

    def telefono_formateado(self):
        if not self.telefono:
            return ''
        if self.ciudad:
            telf = f'+{self.ciudad.provincia.pais.codigotelefono} {self.telefono}'
        else:
            telf = f'{self.telefono}'
        return telf

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = "Perfiles"
        ordering = ('id',)


class CuentaGoogle(ModeloBase):
    """Vínculo de inicio de sesión: una cuenta de Google (por su `sub`, que Google no cambia)
    atada a un solo usuario. No es la conexión de calendario (`agenda.ConexionAplicacion`)."""
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name='cuentas_google', verbose_name='Usuario')
    google_sub = models.CharField(max_length=255, verbose_name='Identificador de Google')
    email = models.EmailField(max_length=254, verbose_name='Correo de Google')
    ultimo_acceso = models.DateTimeField(blank=True, null=True, verbose_name='Último acceso')

    class Meta:
        verbose_name = 'Cuenta de Google vinculada'
        verbose_name_plural = 'Cuentas de Google vinculadas'
        ordering = ['email']
        constraints = [
            models.UniqueConstraint(fields=['google_sub'], condition=models.Q(status=True),
                                    name='cuentagoogle_sub_unico_activo'),
            models.UniqueConstraint(fields=['usuario'], condition=models.Q(status=True),
                                    name='cuentagoogle_usuario_unico_activo'),
        ]

    def __str__(self):
        return f'{self.email} → {self.usuario.username}'
