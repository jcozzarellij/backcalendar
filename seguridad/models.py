from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

from core.crypto import EncryptedTextField
from core.custom_models import ModeloBase, NormalModel
from core.validadores import FileMaxSizeInMbValidator
from backcalendar.settings import AUTH_USER_MODEL


class ErrorLog(models.Model):
    """Log de excepciones. Sin `ModeloBase` a propósito: es una serie append-only del sistema,
    no una entidad que alguien edite o borre desde el panel."""
    usuario = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name='Usuario', blank=True, null=True)
    archivo = models.TextField(verbose_name='Archivo', blank=True, null=True)
    metodo = models.CharField(max_length=100, verbose_name='Metodo', blank=True, null=True)
    accion = models.CharField(max_length=100, verbose_name='Acción', blank=True, null=True)
    tipo = models.CharField(max_length=100, verbose_name='Tipo Error', blank=True, null=True)
    linea = models.CharField(max_length=100, verbose_name='Linea', blank=True, null=True)
    descripcion = models.TextField(verbose_name='Descripción', blank=True, null=True)
    corregido = models.BooleanField(default=False, verbose_name="¿Error Corregido?")
    fecha = models.DateTimeField(verbose_name='Fecha', auto_now_add=True)

    def save(self, force_insert=False, force_update=False, using=None, **kwargs):
        self.accion = self.accion.upper()
        super(ErrorLog, self).save(force_insert, force_update, using)

    def __str__(self):
        return "{} - {} - {} [{}]".format(self.tipo, self.linea, self.descripcion, self.accion)

    class Meta:
        verbose_name = 'ErrorLog'
        verbose_name_plural = 'ErrorLogs'
        ordering = ('-fecha', 'pk')


class AudiUsuarioTabla(models.Model):
    """Auditoría de quién tocó qué registro. Sin `ModeloBase` a propósito: es la tabla que
    REGISTRA la auditoría de los demás; darle soft-delete permitiría tapar el rastro que
    justifica su existencia. `purgar_historicos` también la excluye."""
    usuario = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name='Usuario', editable=False)
    usuario_admin = models.ForeignKey(AUTH_USER_MODEL, editable=False, on_delete=models.PROTECT,
                                      verbose_name='Usuario Administrador', blank=True, null=True,
                                      related_name="fk_usuario_admin")
    # GenericForeignKey
    content_type = models.ForeignKey("contenttypes.ContentType", on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    modelo = GenericForeignKey('content_type', 'object_id')
    # ----------------------------------------------------------------
    registroname = models.CharField(max_length=1000, editable=False, verbose_name='Registro Name')
    accion = models.CharField(max_length=100, verbose_name='Acción', editable=False)
    fecha = models.DateTimeField(verbose_name='Fecha', auto_now_add=True)
    datos_json = models.TextField(verbose_name="Datos en formato json", null=True, blank=True, editable=False)
    ip = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Ip')

    def save(self, force_insert=False, force_update=False, using=None, **kwargs):
        self.registroname = str(self.registroname).upper()
        self.accion = self.accion.upper()
        super(AudiUsuarioTabla, self).save(force_insert, force_update, using)

    def __str__(self):
        return "{} - {} - {} [{}]".format(self.usuario.username, self.modelo.__class__.__name__ if self.modelo else '', self.registroname, self.accion)

    class Meta:
        verbose_name = 'Auditoría Usuario'
        verbose_name_plural = 'Auditorías Usuarios'
        ordering = ('-fecha', 'pk')


PRIORIDAD_NOTIFICACION = (
    (1, u'Alta'),
    (2, u'Media'),
    (3, u'Baja')
)

TIPO_NOTIFICACION = (
    (1, u'Mensaje'),
    (2, u'Proceso'),
    (3, u'Información'),
    (4, u'Error')
)


class Notificacion(ModeloBase):
    titulo = models.CharField(verbose_name=u'Titulo de la Notificación', max_length=300, null=True, blank=True)
    cuerpo = models.TextField(verbose_name=u'Cuerpo de la Notificación', null=True, blank=True)
    destinatario = models.ForeignKey('autenticacion.Usuario', verbose_name=u'Destinatario', on_delete=models.CASCADE)
    url = models.CharField(verbose_name=u'URL de enlace directo', max_length=300, null=True, blank=True)
    leido = models.BooleanField(default=False, verbose_name=u'Leído')
    fecha_hora_leido = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha y hora de leido')
    fecha_hora_visible = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha y hora visible')
    prioridad = models.IntegerField(choices=PRIORIDAD_NOTIFICACION, null=True, blank=True, verbose_name=u'Prioridad')
    tipo = models.IntegerField(choices=TIPO_NOTIFICACION, default=1, verbose_name=u'Tipo Notificación')
    en_proceso = models.BooleanField(default=False, verbose_name='En Proceso')
    error = models.BooleanField(default=False, verbose_name='Error al ejecutar el reporte')

    def __str__(self):
        return u'Notificación: %s - Para: %s' % (self.titulo, self.destinatario)

    def diasingresado(self):
        # fecha_registro es DateTimeField (ver ModeloBase). Antes se intentaba combinar
        # con self.hora_registro, que no existe como campo → AttributeError.
        fh = self.fecha_registro
        if fh is None:
            return ''
        if isinstance(fh, datetime):
            fecha_hora_registro = fh
        else:
            # En caso extremo de que sea un date, asume medianoche
            fecha_hora_registro = datetime.combine(fh, datetime.min.time())
        # Normalizar timezone para la resta
        tiempo_actual = timezone.now()
        if timezone.is_aware(tiempo_actual) and timezone.is_naive(fecha_hora_registro):
            fecha_hora_registro = timezone.make_aware(fecha_hora_registro, timezone.get_current_timezone())
        elif timezone.is_naive(tiempo_actual) and timezone.is_aware(fecha_hora_registro):
            tiempo_actual = timezone.make_aware(tiempo_actual, timezone.get_current_timezone())
        tiempo_transcurrido = tiempo_actual - fecha_hora_registro
        dias = tiempo_transcurrido.days
        segundos = tiempo_transcurrido.seconds
        horas = segundos // 3600
        minutos = (segundos // 60) % 60
        segundos = segundos % 60
        return f"{dias} días, {horas} horas, {minutos} minutos, {segundos} segundos"

    def save(self, *args, **kwargs):
        es_nuevo = self._state.adding
        super(Notificacion, self).save(*args, **kwargs)
        if es_nuevo and self.destinatario_id:
            self._disparar_webpush()

    def _disparar_webpush(self):
        try:
            from pwa.notificaciones import enviar_push_usuario
        except ImportError:
            return
        try:
            head = (self.titulo or 'Nueva notificación').strip()[:120] or 'Nueva notificación'
            body = (self.cuerpo or '').strip()[:200]
            enviar_push_usuario(
                self.destinatario,
                head=head,
                body=body,
                url=(self.url or None),
                tag=f'notif-{self.pk}',
                require_interaction=(self.prioridad == 1),
                extra={'tipo': self.tipo, 'prioridad': self.prioridad, 'notif_id': self.pk},
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                'No se pudo disparar webpush para Notificacion %s', self.pk,
            )

    class Meta:
        verbose_name = u"Notificación"
        verbose_name_plural = u"Notificaciones"
        ordering = ['destinatario', 'fecha_registro', ]


class Configuracion(ModeloBase):
    nombre_empresa = models.CharField(max_length=1000, verbose_name='Nombre de la Empresa')
    alias = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Alias')
    titulo = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Título Web')
    descripcion = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Descripción Web')
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name='Teléfono Empresa')
    email = models.CharField(max_length=100, blank=True, null=True, verbose_name='Email Empresa')
    web = models.CharField(max_length=100, blank=True, null=True, verbose_name='Web')
    email_notificacion = models.CharField(max_length=100, blank=True, null=True, verbose_name='Email Notificaciones')
    direccion = models.CharField(max_length=5000, blank=True, null=True, verbose_name='Dirección Empresa')
    terminosycondiciones = models.TextField(blank=True, null=True, verbose_name='Terminos y Condiciones')
    # DATOS LOGOS/FONDOS
    ico = models.FileField(upload_to='configuracion/', max_length=600, blank=True, null=True, verbose_name='Favicon', validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'tiff', 'webp', "jfif"]), FileMaxSizeInMbValidator(8)])
    logo_sistema = models.FileField(upload_to='configuracion/', validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'tiff', 'webp', "jfif"]), FileMaxSizeInMbValidator(8)], max_length=600, blank=True, null=True, verbose_name='Logo')
    logo_sistema_white = models.FileField(upload_to='configuracion/', validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'tiff', 'webp', "jfif"]), FileMaxSizeInMbValidator(8)], max_length=600, blank=True, null=True, verbose_name='Logo Blanco')
    fondo_landing = models.FileField(upload_to='configuracion/', validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']), FileMaxSizeInMbValidator(8)], max_length=600, blank=True, null=True, verbose_name='Fondo de la portada', help_text='Foto ancha (mínimo 1600 px) que se ve detrás del título de la página de inicio.')

    pg_dump_cmd = models.CharField(
        max_length=1000, blank=True, null=True, verbose_name='Ruta de pg_dump (backups)',
        help_text='Ruta al ejecutable pg_dump para los backups de BD (ej. '
                  'C:\\Program Files\\PostgreSQL\\15\\bin\\pg_dump.exe). Vacío = se busca en el '
                  'PATH o en credenciales.json; si no está, el backup cae a dumpdata JSON.'
    )
    backup_retencion = models.PositiveSmallIntegerField(
        default=15, verbose_name='Backups a conservar',
        help_text='Cuántos backups de BD se guardan antes de rotar (borrar los más viejos).'
    )

    google_client_id = models.CharField(max_length=300, blank=True, default='', verbose_name='ID de cliente de Google',
                                        help_text='Google Cloud › Google Auth Platform › Clientes. Termina en .apps.googleusercontent.com.')
    google_client_secret = EncryptedTextField(blank=True, default='', verbose_name='Secreto de cliente de Google',
                                              help_text='Se guarda cifrado. Déjalo vacío para conservar el actual.')
    google_redirect_uri = models.CharField(max_length=500, blank=True, default='', verbose_name='URI de redirección de Google',
                                           help_text='Vacío = la URI por defecto del sistema, que se muestra arriba.')
    conexion_google = models.BooleanField(default=False, verbose_name='Permitir inicio de sesión con Google',
                                          help_text='Muestra «Continuar con Google» en /login/. Solo entran correos de los '
                                                    'dominios permitidos que ya pertenezcan a un usuario.')
    teams_client_id = models.CharField(max_length=300, blank=True, default='', verbose_name='ID de aplicación (cliente) de Microsoft',
                                       help_text='Microsoft Entra › Registros de aplicaciones › Información general.')
    teams_client_secret = EncryptedTextField(blank=True, default='', verbose_name='Secreto de cliente de Microsoft',
                                             help_text='Se guarda cifrado. Déjalo vacío para conservar el actual.')
    teams_tenant_id = models.CharField(max_length=100, blank=True, default='', verbose_name='ID de directorio (inquilino) de Microsoft',
                                       help_text='Vacío = «common», para cuentas de cualquier organización.')
    teams_redirect_uri = models.CharField(max_length=500, blank=True, default='', verbose_name='URI de redirección de Microsoft')
    zoom_client_id = models.CharField(max_length=300, blank=True, default='', verbose_name='Client ID de Zoom',
                                      help_text='Zoom App Marketplace › tu app OAuth › App Credentials.')
    zoom_client_secret = EncryptedTextField(blank=True, default='', verbose_name='Client Secret de Zoom',
                                            help_text='Se guarda cifrado. Déjalo vacío para conservar el actual.')
    zoom_redirect_uri = models.CharField(max_length=500, blank=True, default='', verbose_name='URI de redirección de Zoom')

    CACHE_CLAVE = 'seguridad:configuracion:instancia'

    @staticmethod
    def get_instancia():
        """Configuración del sistema, cacheada. La lee el middleware en CADA request para
        armar `request.config`, y sin cache eso son 2-3 consultas por petición (incluida la
        introspección de `db_table_exists`) hasta para una página estática o el health check.

        Se invalida al guardar (`save`). El TTL corto es la red de seguridad por si alguien
        edita la fila fuera de la aplicación."""
        from django.core.cache import cache
        from core.funciones import db_table_exists

        try:
            cacheada = cache.get(Configuracion.CACHE_CLAVE)
        except Exception:
            cacheada = None
        if cacheada is not None:
            return cacheada

        try:
            confi = Configuracion.objects.first() if db_table_exists(
                Configuracion._meta.db_table) and Configuracion.objects.count() > 0 else Configuracion()
        except Exception as ex:
            confi = Configuracion()
        if confi.pk:
            # Solo se cachea la fila real: la instancia vacía es el caso «todavía no migrado»
            # y cachearla dejaría al sitio sin configuración hasta que venza el TTL.
            try:
                cache.set(Configuracion.CACHE_CLAVE, confi, timeout=300)
            except Exception:
                pass
        return confi

    @staticmethod
    def limpiar_cache():
        from django.core.cache import cache
        try:
            cache.delete(Configuracion.CACHE_CLAVE)
        except Exception:
            pass

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Configuracion.limpiar_cache()

    class Meta:
        verbose_name = 'Configuración'
        verbose_name_plural = 'Configuración'
        permissions = (
            ("can_view_auditoria", "Puede ver auditorías"),
        )


class Modulo(ModeloBase):
    url = models.CharField(max_length=100)
    nombre = models.CharField(max_length=100)
    orden = models.IntegerField(default=0)
    icono = models.CharField(max_length=100, blank=True, null=True, verbose_name='Ícono')

    def __str__(self):
        return '{} ({})'.format(self.nombre, self.url)

    class Meta:
        verbose_name = 'URL del Sidebar'
        verbose_name_plural = 'URLs del Sidebar'
        ordering = ['nombre']


class GroupModulo(ModeloBase):
    group = models.OneToOneField(Group, on_delete=models.CASCADE)
    modulos = models.ManyToManyField(Modulo)

    def __str__(self):
        return '{}'.format(self.group.name)

    def modulos_activos(self):
        """Los del rol que siguen vivos. `modulos.all` traería también los dados de baja, y la
        plantilla no puede filtrar: por eso el listado y el sidebar llaman a este método."""
        return self.modulos.filter(status=True).order_by('orden')

    class Meta:
        verbose_name = 'Asignar Urls a cada rol de usuario'
        verbose_name_plural = 'Asignar Urls a cada rol de usuario'
        ordering = ('pk',)


class ModuloGrupo(ModeloBase):
    nombre = models.CharField(max_length=100)
    icono = models.CharField(max_length=100)
    modulos = models.ManyToManyField(Modulo)
    prioridad = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return '{} {}'.format(self.nombre, self.prioridad)

    class Meta:
        verbose_name = 'Grupo de URLs del Sidebar'
        verbose_name_plural = 'Grupos de URLs del Sidebar'
        ordering = ('prioridad', 'nombre')
        # permissions = (
        #     ('')
        # )

    def modulos_activos(self):
        return self.modulos.filter(status=True).order_by('orden')

def slug_name(self):
    from django.utils.text import slugify
    return slugify(self.name)


Group.add_to_class("slug_name", slug_name)


class SessionUser(NormalModel):
    """Dispositivo desde el que entró un usuario. Hereda `NormalModel` y no `ModeloBase` porque
    su ciclo de vida es el de la sesión de Django: al cerrarla, la fila se borra de verdad
    (CASCADE desde `sessions.Session`), y una fila con `status=False` seguiría ocupando el
    OneToOne de una sesión ya muerta."""
    user = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE)
    session = models.OneToOneField("sessions.Session", on_delete=models.CASCADE)
    dispositivo = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Dispositivo')
    ip = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Ip')
    codigounico = models.TextField("Código Único de navegador")
    fecha_conexion = models.DateTimeField(auto_now_add=True)
    areageografica = models.CharField("Área Geográfica", max_length=500, null=True, blank=True)

    @staticmethod
    def nuevo(request):
        from core.funciones import get_client_ip
        from django.contrib.sessions.models import Session
        ucc = SessionUser.objects.get_or_create(session_id=Session.objects.get(session_key=request.session.session_key).pk,
                                                   user_id=request.user.pk, codigounico=request.COOKIES.get('SISTEMA_DEVICE_ID') or 'SINCODIGO')[0]
        ucc.fecha_conexion = datetime.now()
        ucc.ip = get_client_ip(request)
        ucc.save()
        return ucc




class CronLogEjecucion(models.Model):
    """Bitácora de cada corrida de cron. Sin `ModeloBase` a propósito: serie append-only que se
    poda por antigüedad con un DELETE real (`purgar_historicos`), no con soft-delete."""
    proceso = models.TextField(verbose_name='Proceso', blank=True, null=True)
    detalle = models.TextField(verbose_name='Detalle de Ejecución', blank=True, null=True)
    fecha = models.DateField(verbose_name='Fecha', auto_now_add=True)
    hora = models.TimeField(verbose_name='Hora', auto_now_add=True)
    conexito = models.BooleanField(default=True, verbose_name='Con Exito')

    def save(self, force_insert=False, force_update=False, using=None, **kwargs):
        super(CronLogEjecucion, self).save(force_insert, force_update, using)

    def __str__(self):
        return f"{self.fecha} {self.hora} - {self.proceso} - {self.detalle}"

    class Meta:
        verbose_name = 'Log de Ejecución'
        verbose_name_plural = 'Log de Ejecución'
        ordering = ('-fecha', 'pk')


PARAMETRO_TIPO_CHOICES = (
    ('entero', 'Número entero'),
    ('decimal', 'Número decimal'),
    ('texto', 'Texto'),
    ('url', 'URL'),
    ('booleano', 'Sí / No'),
)

PARAMETRO_GRUPO_CHOICES = (
    ('urls', 'URLs y endpoints'),
    ('general', 'General'),
    ('tiempos', 'Agenda: tiempos'),
    ('portal', 'Agenda: portal de reserva'),
    ('cliente', 'Agenda: clientes'),
    ('recordatorios', 'Agenda: recordatorios'),
)


class ParametroSistema(ModeloBase):
    """Parámetros de comportamiento del sistema editables desde la UI (sin tocar código ni
    credenciales.json). Tabla clave→valor autoexplicativa: cada fila trae su `descripcion`.
    Prioridad de lectura: esta tabla →
    settings/credenciales.json → default de código. Cacheada por clave para no pegarle a la BD
    en cada consulta."""
    clave = models.CharField(max_length=100, unique=True, verbose_name='Clave')
    etiqueta = models.CharField(max_length=200, verbose_name='Nombre visible')
    descripcion = models.TextField(blank=True, null=True, verbose_name='¿Qué hace? (explicación)')
    grupo = models.CharField(max_length=40, choices=PARAMETRO_GRUPO_CHOICES, default='general', verbose_name='Grupo')
    tipo = models.CharField(max_length=20, choices=PARAMETRO_TIPO_CHOICES, default='texto', verbose_name='Tipo de dato')
    valor = models.TextField(blank=True, null=True, verbose_name='Valor')
    valor_default = models.TextField(blank=True, null=True, verbose_name='Valor por defecto')
    unidad = models.CharField(max_length=40, blank=True, null=True, verbose_name='Unidad / referencia')
    orden = models.PositiveIntegerField(default=0, verbose_name='Orden')
    editable = models.BooleanField(default=True, verbose_name='Editable')

    def __str__(self):
        return f'{self.clave} = {self.valor}'

    @staticmethod
    def _cache_key(clave):
        return f'parametro_sistema__{clave}'

    def _castear(self, crudo):
        if crudo is None:
            return None
        crudo = str(crudo).strip()
        try:
            if self.tipo == 'entero':
                return int(float(crudo))
            if self.tipo == 'decimal':
                return Decimal(crudo)
            if self.tipo == 'booleano':
                return crudo.lower() in ('1', 'true', 'si', 'sí', 'on', 'yes')
        except (ValueError, ArithmeticError):
            return None
        return crudo

    @classmethod
    def valor_de(cls, clave, default=None):
        """Valor vigente de un parámetro, casteado a su tipo. Cacheado 60s. Si la tabla o la
        fila no existen todavía (primer arranque, seeder no corrido) devuelve `default` — así
        nada se rompe por falta de configuración."""
        from django.core.cache import cache
        from core.funciones import db_table_exists

        ck = cls._cache_key(clave)
        cacheado = cache.get(ck)
        if cacheado is not None:
            return cacheado[0]
        valor = default
        try:
            if db_table_exists(cls._meta.db_table):
                fila = cls.objects.filter(clave=clave, status=True).first()
                if fila is not None:
                    casteado = fila._castear(fila.valor)
                    if casteado is not None and not (isinstance(casteado, str) and casteado == ''):
                        valor = casteado
        except Exception:
            valor = default
        cache.set(ck, (valor,), 60)
        return valor

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from django.core.cache import cache
        cache.delete(self._cache_key(self.clave))

    class Meta:
        verbose_name = 'Parámetro del sistema'
        verbose_name_plural = 'Parámetros del sistema'
        ordering = ['grupo', 'orden', 'clave']

CRON_PERIODICIDAD_CHOICES = [
    ('*/5 * * * *', 'Cada 5 minutos'),
    ('*/10 * * * *', 'Cada 10 minutos'),
    ('*/15 * * * *', 'Cada 15 minutos'),
    ('*/30 * * * *', 'Cada 30 minutos'),
    ('0 * * * *', 'Cada hora'),
    ('0 2 * * *', 'Todos los días 02:00'),
    ('15 3 * * *', 'Todos los días 03:15'),
    ('30 3 * * *', 'Todos los días 03:30'),
    ('0 4 * * 6', 'Sábados 04:00'),
    ('30 3 * * 0', 'Domingos 03:30'),
    ('personalizado', 'Personalizado (expresión cron)'),
]


class TareaCron(ModeloBase):
    """Registro editable de las tareas programadas (crons). Es la fuente de verdad del PANEL:
    permite activar/desactivar y cambiar la periodicidad SIN entrar por SSH.

    Cómo se aplica cada campo:
    - `activo`: cada comando de cron chequea `cron_activo(clave)` al arrancar y sale sin
      trabajar si está en False. Así se apaga un cron desde la web aunque el crontab lo dispare
      igual (el script hace no-op). Efecto inmediato.
    - `schedule`: la periodicidad deseada. El management command `sync_crontab` (corrido por root)
      reescribe el crontab real desde estas filas, así un cambio de horario en la web se aplica
      en la próxima sincronización. Cambiar el horado NO es inmediato: depende del sync.
    - `ultima_ejecucion`/`ultimo_exito`: heartbeat que escribe el propio script al terminar
      (`heartbeat_cron`). El panel los cruza con `schedule` para marcar «caído» (debió correr y
      no lo hizo) vs «activo» vs «apagado»."""
    clave = models.CharField(max_length=60, unique=True, db_index=True, verbose_name='Clave')
    nombre = models.CharField(max_length=120, verbose_name='Nombre')
    comando = models.CharField(max_length=255, verbose_name='Comando')
    schedule = models.CharField(max_length=60, default='0 4 * * 6', verbose_name='Periodicidad (cron)')
    descripcion = models.TextField(blank=True, default='', verbose_name='Qué hace')
    log = models.CharField(max_length=80, blank=True, default='', verbose_name='Archivo de log')
    icono = models.CharField(max_length=40, blank=True, default='bi-clock', verbose_name='Ícono')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    gestionado_crontab = models.BooleanField(
        default=True, verbose_name='Lo gestiona el crontab',
        help_text='Si está activo, sync_crontab escribe su línea en el crontab real. Apagarlo '
                  'deja el cron fuera del crontab (queda solo como registro/apagado).',
    )
    orden = models.IntegerField(default=0, verbose_name='Orden')
    ultima_ejecucion = models.DateTimeField(null=True, blank=True, verbose_name='Última ejecución')
    ultimo_exito = models.BooleanField(null=True, blank=True, verbose_name='Último resultado OK')
    ultimo_detalle = models.CharField(max_length=300, blank=True, default='', verbose_name='Último detalle')
    ultima_duracion_seg = models.IntegerField(null=True, blank=True, verbose_name='Duración (s)')

    class Meta:
        verbose_name = 'Tarea programada (cron)'
        verbose_name_plural = 'Tareas programadas (cron)'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return f'{self.nombre} ({self.schedule})'


class DominioCorreoPermitido(ModeloBase):
    """Dominios de correo con los que se puede iniciar sesión con Google (ej. `gmail.com`).
    Sin filas activas nadie entra con Google."""
    dominio = models.CharField(max_length=150, verbose_name='Dominio',
                               help_text='Solo el dominio, sin @. Ej.: excudere.com o gmail.com.')
    descripcion = models.CharField(max_length=300, blank=True, default='', verbose_name='Descripción')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    @staticmethod
    def normalizar(dominio):
        return (dominio or '').strip().lower().lstrip('@').strip()

    def save(self, *args, **kwargs):
        self.dominio = DominioCorreoPermitido.normalizar(self.dominio)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Dominio de correo permitido'
        verbose_name_plural = 'Dominios de correo permitidos'
        ordering = ['dominio']
        constraints = [
            models.UniqueConstraint(fields=['dominio'], condition=models.Q(status=True),
                                    name='dominiocorreo_dominio_unico_activo'),
        ]

    def __str__(self):
        return self.dominio
