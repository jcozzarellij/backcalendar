from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import F, Q

from backcalendar.settings import AUTH_USER_MODEL
from core.crypto import EncryptedTextField
from core.custom_models import ModeloBase
from core.validadores import validate_file_size_2mb

ROL_MIEMBRO = (
    ('responsable', 'Responsable'),
    ('copia', 'En copia'),
)

DIA_SEMANA = (
    (0, 'Lunes'),
    (1, 'Martes'),
    (2, 'Miércoles'),
    (3, 'Jueves'),
    (4, 'Viernes'),
    (5, 'Sábado'),
    (6, 'Domingo'),
)

TIPO_EXCEPCION = (
    ('vacaciones', 'Vacaciones'),
    ('permiso', 'Permiso'),
    ('horario_especial', 'Horario especial'),
)


class Proyecto(ModeloBase):
    codigo = models.SlugField(max_length=40, verbose_name='Código')
    nombre = models.CharField(max_length=150, verbose_name='Nombre')
    lider = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, blank=True, null=True,
                              related_name='proyectos_liderados', verbose_name='Líder del proyecto')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        ordering = ('nombre',)
        constraints = [
            models.UniqueConstraint(fields=['codigo'], name='proyecto_codigo_unico', condition=Q(status=True)),
        ]


class Equipo(ModeloBase):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.PROTECT, related_name='equipos', verbose_name='Proyecto')
    nombre = models.CharField(max_length=150, verbose_name='Nombre')
    lider = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, blank=True, null=True,
                              related_name='equipos_liderados', verbose_name='Líder del equipo')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    def __str__(self):
        return f'{self.nombre} · {self.proyecto}'

    class Meta:
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'
        ordering = ('proyecto__nombre', 'nombre')
        constraints = [
            models.UniqueConstraint(fields=['proyecto', 'nombre'], name='equipo_nombre_unico',
                                    condition=Q(status=True)),
        ]


class MiembroEquipo(ModeloBase):
    """Un usuario puede estar en varios equipos. Solo los responsables bloquean la búsqueda de
    espacio; los que van en copia reciben la invitación pero no condicionan el horario."""
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name='miembros', verbose_name='Equipo')
    usuario = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='membresias_agenda',
                                verbose_name='Usuario')
    rol = models.CharField(max_length=20, choices=ROL_MIEMBRO, default='responsable', verbose_name='Rol')

    def __str__(self):
        return f'{self.usuario} · {self.get_rol_display()}'

    class Meta:
        verbose_name = 'Miembro de equipo'
        verbose_name_plural = 'Miembros de equipo'
        ordering = ('rol', 'usuario__first_name')
        constraints = [
            models.UniqueConstraint(fields=['equipo', 'usuario'], name='miembro_equipo_unico',
                                    condition=Q(status=True)),
        ]


class PatronTurno(ModeloBase):
    """Semana tipo de un usuario con su vigencia. No se guarda un registro por fecha: la
    disponibilidad de un día sale del patrón vigente menos excepciones y feriados."""
    usuario = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='patrones_turno',
                                verbose_name='Usuario')
    vigencia_desde = models.DateField(verbose_name='Vigente desde')
    vigencia_hasta = models.DateField(blank=True, null=True, verbose_name='Vigente hasta')

    def __str__(self):
        hasta = self.vigencia_hasta.strftime('%d/%m/%Y') if self.vigencia_hasta else 'sin fin'
        return f'{self.usuario} · {self.vigencia_desde:%d/%m/%Y} a {hasta}'

    class Meta:
        verbose_name = 'Semana tipo'
        verbose_name_plural = 'Semanas tipo'
        ordering = ('usuario', '-vigencia_desde')
        constraints = [
            models.CheckConstraint(condition=Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=F('vigencia_desde')),
                                   name='patron_vigencia_valida'),
        ]


class FranjaTurno(ModeloBase):
    patron = models.ForeignKey(PatronTurno, on_delete=models.PROTECT, related_name='franjas', verbose_name='Semana tipo')
    dia_semana = models.PositiveSmallIntegerField(choices=DIA_SEMANA, verbose_name='Día')
    hora_inicio = models.TimeField(verbose_name='Desde')
    hora_fin = models.TimeField(verbose_name='Hasta')

    def __str__(self):
        return f'{self.get_dia_semana_display()} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}'

    class Meta:
        verbose_name = 'Franja de turno'
        verbose_name_plural = 'Franjas de turno'
        ordering = ('dia_semana', 'hora_inicio')
        constraints = [
            models.CheckConstraint(condition=Q(hora_fin__gt=F('hora_inicio')), name='franja_horas_validas'),
        ]


class ExcepcionTurno(ModeloBase):
    """Días puntuales que se salen de la semana tipo. Sin horas = todo el día no disponible.
    `horario_especial` con horas reemplaza las franjas de esos días por las indicadas."""
    usuario = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='excepciones_turno',
                                verbose_name='Usuario')
    tipo = models.CharField(max_length=20, choices=TIPO_EXCEPCION, default='permiso', verbose_name='Tipo')
    fecha_desde = models.DateField(verbose_name='Desde')
    fecha_hasta = models.DateField(verbose_name='Hasta')
    hora_inicio = models.TimeField(blank=True, null=True, verbose_name='Hora inicio')
    hora_fin = models.TimeField(blank=True, null=True, verbose_name='Hora fin')
    motivo = models.CharField(max_length=200, blank=True, default='', verbose_name='Motivo')

    def __str__(self):
        return f'{self.get_tipo_display()} {self.fecha_desde:%d/%m/%Y}-{self.fecha_hasta:%d/%m/%Y}'

    class Meta:
        verbose_name = 'Excepción de turno'
        verbose_name_plural = 'Excepciones de turno'
        ordering = ('fecha_desde',)
        constraints = [
            models.CheckConstraint(condition=Q(fecha_hasta__gte=F('fecha_desde')), name='excepcion_fechas_validas'),
        ]


class Feriado(ModeloBase):
    fecha = models.DateField(verbose_name='Fecha')
    nombre = models.CharField(max_length=150, verbose_name='Nombre')
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, blank=True, null=True, related_name='feriados',
                               verbose_name='Solo para el equipo')

    def __str__(self):
        return f'{self.fecha:%d/%m/%Y} · {self.nombre}'

    class Meta:
        verbose_name = 'Feriado'
        verbose_name_plural = 'Feriados'
        ordering = ('fecha',)


class Portal(ModeloBase):
    """Portal de reserva con su marca. Un solo dominio: cada portal es una ruta. El marcado
    como `principal` es el que muestra la landing pública."""
    nombre = models.CharField(max_length=150, verbose_name='Nombre')
    slug = models.SlugField(max_length=60, verbose_name='Ruta')
    logo = models.FileField(upload_to='portales/', blank=True, null=True, verbose_name='Logo',
                            validators=[FileExtensionValidator(['png', 'jpg', 'jpeg', 'webp', 'svg']),
                                        validate_file_size_2mb])
    color_principal = models.CharField(max_length=7, default='#005082', verbose_name='Color principal')
    telefono_atencion = models.CharField(max_length=30, blank=True, default='', verbose_name='Teléfono de atención')
    sitios_autorizados = models.TextField(blank=True, default='',
                                          verbose_name='Sitios donde se puede incrustar (uno por línea)')
    principal = models.BooleanField(default=False, verbose_name='Portal principal')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Portal de reserva'
        verbose_name_plural = 'Portales de reserva'
        ordering = ('nombre',)
        constraints = [
            models.UniqueConstraint(fields=['slug'], name='portal_slug_unico', condition=Q(status=True)),
        ]


class Producto(ModeloBase):
    """Producto o subproducto de un portal. Un subproducto es un Producto con `padre`; solo hay
    dos niveles. Los tiempos vacíos heredan del padre y, si no, de los parámetros globales."""
    portal = models.ForeignKey(Portal, on_delete=models.PROTECT, related_name='productos', verbose_name='Portal')
    padre = models.ForeignKey('self', on_delete=models.PROTECT, blank=True, null=True, related_name='subproductos',
                              verbose_name='Producto padre')
    slug = models.SlugField(max_length=60, verbose_name='Ruta')
    nombre = models.CharField(max_length=150, verbose_name='Nombre (español)')
    nombre_en = models.CharField(max_length=150, blank=True, default='', verbose_name='Nombre (inglés)')
    nombre_pt = models.CharField(max_length=150, blank=True, default='', verbose_name='Nombre (portugués)')
    descripcion = models.CharField(max_length=300, blank=True, default='', verbose_name='Descripción (español)')
    descripcion_en = models.CharField(max_length=300, blank=True, default='', verbose_name='Descripción (inglés)')
    descripcion_pt = models.CharField(max_length=300, blank=True, default='', verbose_name='Descripción (portugués)')
    sitio_web = models.URLField(blank=True, default='', verbose_name='Sitio del producto')
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, blank=True, null=True, related_name='productos',
                               verbose_name='Equipo que atiende')
    duracion_min = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Duración (min)')
    antelacion_horas = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Antelación mínima (h)')
    margen_min = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Margen entre citas (min)')
    limite_dia = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Máximo por día')
    limite_semana = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Máximo por semana')
    ventana_dias = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Se puede agendar hasta (días)')
    orden = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    destacado = models.BooleanField(default=False, verbose_name='Destacado en la página principal',
                                    help_text='Sale en el landing (máximo 4). Todo producto activo aparece en el catálogo.')

    def __str__(self):
        return f'{self.padre} · {self.nombre}' if self.padre_id else self.nombre

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ('orden', 'nombre')
        constraints = [
            models.UniqueConstraint(fields=['portal', 'slug'], name='producto_slug_unico',
                                    condition=Q(status=True, padre__isnull=True)),
            models.UniqueConstraint(fields=['padre', 'slug'], name='subproducto_slug_unico',
                                    condition=Q(status=True, padre__isnull=False)),
        ]


PROVEEDOR_APLICACION = (
    ('google', 'Google Calendar'),
    ('microsoft', 'Microsoft Teams'),
    ('zoom', 'Zoom'),
)


class ConexionAplicacion(ModeloBase):
    """Cuenta externa que un usuario conecta desde «Conexiones» (Google Calendar hoy;
    Teams y Zoom después). El refresh token va cifrado; el access token no se guarda."""
    usuario = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='conexiones_aplicacion',
                                verbose_name='Usuario')
    proveedor = models.CharField(max_length=20, choices=PROVEEDOR_APLICACION, verbose_name='Proveedor')
    cuenta = models.CharField(max_length=200, blank=True, default='', verbose_name='Cuenta conectada')
    refresh_token = EncryptedTextField(blank=True, default='', verbose_name='Token de renovación')
    scopes = models.TextField(blank=True, default='', verbose_name='Permisos concedidos')
    calendario_id = models.CharField(max_length=200, blank=True, default='primary', verbose_name='Calendario')
    conectada = models.BooleanField(default=False, verbose_name='Conectada')
    ultima_verificacion = models.DateTimeField(blank=True, null=True, verbose_name='Última verificación')
    ultimo_error = models.CharField(max_length=300, blank=True, default='', verbose_name='Último error')

    def __str__(self):
        return f'{self.usuario} · {self.get_proveedor_display()} · {self.cuenta or "sin cuenta"}'

    class Meta:
        verbose_name = 'Conexión de aplicación'
        verbose_name_plural = 'Conexiones de aplicaciones'
        ordering = ('usuario', 'proveedor')
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'proveedor'], name='conexion_aplicacion_unica',
                                    condition=Q(status=True)),
        ]


from .models_citas import *
