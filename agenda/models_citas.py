from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeBoundary, RangeOperators
from django.db import models
from django.db.models import F, Func, Q

from backcalendar.settings import AUTH_USER_MODEL
from core.custom_models import ModeloBase, RegistroInmutable
from .models import PLATAFORMA_REUNION, Equipo, Portal, Producto, Proyecto, Reunion

ESTADO_SOLICITUD = (
    ('en_cola', 'En cola'),
    ('asignada', 'Asignada'),
    ('realizada', 'Realizada'),
    ('cerrada', 'Cerrada'),
    ('cancelada', 'Cancelada'),
)

ORIGEN_SOLICITUD = (
    ('portal', 'Portal de reserva'),
    ('panel', 'Panel'),
    ('telefono', 'Teléfono'),
)

ESTADO_CITA = (
    ('confirmada', 'Confirmada'),
    ('pendiente', 'Pendiente de confirmar'),
    ('realizada', 'Realizada'),
    ('cerrada', 'Cerrada'),
    ('no_asistio', 'No asistió'),
    ('cancelada', 'Cancelada'),
)

ESTADOS_CITA_ACTIVOS = ('confirmada', 'pendiente', 'realizada')

ASIGNADA_POR = (
    ('cliente', 'El cliente'),
    ('sistema', 'El sistema'),
    ('coordinador', 'El coordinador'),
)

ROL_PARTICIPANTE = (
    ('organizador', 'Organizador'),
    ('responsable', 'Responsable'),
    ('copia', 'En copia'),
)

RESPUESTA_INVITACION = (
    ('pendiente', 'Sin responder'),
    ('acepto', 'Aceptó'),
    ('rechazo', 'Rechazó'),
)

TIPO_REUNION = (
    ('demostracion', 'Demostración'),
    ('soporte', 'Soporte de plataforma'),
    ('proforma', 'Proforma'),
    ('seguimiento', 'Seguimiento'),
    ('otro', 'Otro'),
)

FUENTE_BLOQUEO = (
    ('cita', 'Cita'),
    ('google', 'Google Calendar'),
    ('manual', 'Bloqueo manual'),
)

IDIOMA_CLIENTE = (
    ('es', 'Español'),
    ('en', 'Inglés'),
    ('pt', 'Portugués'),
)


class TsTzRange(Func):
    function = 'tstzrange'
    output_field = DateTimeRangeField()


class Cliente(ModeloBase):
    """Persona externa que agenda. Se crea sola con la primera cita; el correo evita duplicados."""
    codigo = models.CharField(max_length=20, verbose_name='Código')
    nombres = models.CharField(max_length=200, verbose_name='Nombres y apellidos')
    correo = models.EmailField(verbose_name='Correo')
    telefono = models.CharField(max_length=40, blank=True, default='', verbose_name='Teléfono o WhatsApp')
    idioma = models.CharField(max_length=2, choices=IDIOMA_CLIENTE, default='es', verbose_name='Idioma')
    zona_horaria = models.CharField(max_length=64, default='America/Guayaquil', verbose_name='Zona horaria')
    portal_origen = models.ForeignKey(Portal, on_delete=models.PROTECT, blank=True, null=True,
                                      related_name='clientes', verbose_name='Portal de origen')
    nota_privada = models.TextField(blank=True, default='', verbose_name='Nota privada del equipo')

    def __str__(self):
        return self.nombres

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ('nombres',)
        constraints = [
            models.UniqueConstraint(fields=['codigo'], name='cliente_codigo_unico', condition=Q(status=True)),
            models.UniqueConstraint(fields=['correo'], name='cliente_correo_unico', condition=Q(status=True)),
        ]


class Solicitud(ModeloBase):
    """Lo que pide el cliente o registra el equipo. Termina en una cita o espera en la cola."""
    codigo = models.CharField(max_length=20, verbose_name='Referencia')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='solicitudes', verbose_name='Cliente')
    portal = models.ForeignKey(Portal, on_delete=models.PROTECT, blank=True, null=True, related_name='solicitudes',
                               verbose_name='Portal')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, blank=True, null=True, related_name='solicitudes',
                                 verbose_name='Producto')
    proyecto = models.ForeignKey(Proyecto, on_delete=models.PROTECT, blank=True, null=True, related_name='solicitudes',
                                 verbose_name='Proyecto')
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, blank=True, null=True, related_name='solicitudes',
                               verbose_name='Equipo')
    motivo = models.CharField(max_length=300, blank=True, default='', verbose_name='Motivo')
    mensaje = models.TextField(blank=True, default='', verbose_name='Mensaje del cliente')
    origen = models.CharField(max_length=20, choices=ORIGEN_SOLICITUD, default='panel', verbose_name='Origen')
    estado = models.CharField(max_length=20, choices=ESTADO_SOLICITUD, default='en_cola', verbose_name='Estado')
    telefono_para_llamar = models.CharField(max_length=40, blank=True, default='', verbose_name='Pidió que le llamen al')
    causa_cola = models.CharField(max_length=200, blank=True, default='', verbose_name='Por qué está en cola')

    def __str__(self):
        return f'{self.codigo} · {self.cliente}'

    class Meta:
        verbose_name = 'Solicitud'
        verbose_name_plural = 'Solicitudes'
        ordering = ('-fecha_registro',)
        constraints = [
            models.UniqueConstraint(fields=['codigo'], name='solicitud_codigo_unico', condition=Q(status=True)),
        ]


class Cita(ModeloBase):
    """La reunión asignada. Es la fuente de verdad; Google Calendar es el canal."""
    codigo = models.CharField(max_length=20, verbose_name='Código')
    solicitud = models.ForeignKey(Solicitud, on_delete=models.PROTECT, blank=True, null=True, related_name='citas',
                                  verbose_name='Solicitud')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='citas', verbose_name='Cliente')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, blank=True, null=True, related_name='citas',
                                 verbose_name='Producto')
    proyecto = models.ForeignKey(Proyecto, on_delete=models.PROTECT, blank=True, null=True, related_name='citas',
                                 verbose_name='Proyecto')
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, blank=True, null=True, related_name='citas',
                               verbose_name='Equipo')
    organizador = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='citas_organizadas',
                                    verbose_name='Organizador')
    titulo = models.CharField(max_length=200, verbose_name='Título')
    inicio = models.DateTimeField(verbose_name='Inicio')
    fin = models.DateTimeField(verbose_name='Fin')
    estado = models.CharField(max_length=20, choices=ESTADO_CITA, default='confirmada', verbose_name='Estado')
    asignada_por = models.CharField(max_length=20, choices=ASIGNADA_POR, default='coordinador', verbose_name='Asignada por')
    numero_sesion = models.PositiveSmallIntegerField(default=1, verbose_name='Sesión número')
    idioma = models.CharField(max_length=2, choices=IDIOMA_CLIENTE, default='es', verbose_name='Idioma')
    plataforma = models.CharField(max_length=20, choices=PLATAFORMA_REUNION, default='google', verbose_name='Plataforma de la videollamada')
    google_event_id = models.CharField(max_length=255, blank=True, default='', verbose_name='Evento en Google')
    enlace_meet = models.URLField(blank=True, default='', verbose_name='Enlace de videollamada')
    enlace_evento = models.URLField(blank=True, default='', verbose_name='Enlace del evento')
    sincronizada_google = models.BooleanField(default=False, verbose_name='Sincronizada con Google')
    error_google = models.CharField(max_length=300, blank=True, default='', verbose_name='Último error con Google')
    motivo_cancelacion = models.CharField(max_length=300, blank=True, default='', verbose_name='Motivo de cancelación')

    def __str__(self):
        return f'{self.codigo} · {self.titulo}'

    @property
    def duracion_min(self):
        return int((self.fin - self.inicio).total_seconds() // 60)

    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ('inicio',)
        indexes = [
            models.Index(fields=['organizador', 'inicio'], name='cita_organizador_inicio'),
            models.Index(fields=['estado', 'inicio'], name='cita_estado_inicio'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['codigo'], name='cita_codigo_unico', condition=Q(status=True)),
            models.CheckConstraint(condition=Q(fin__gt=F('inicio')), name='cita_rango_valido'),
        ]


class ParticipanteCita(ModeloBase):
    cita = models.ForeignKey(Cita, on_delete=models.PROTECT, related_name='participantes', verbose_name='Cita')
    usuario = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='participaciones',
                                verbose_name='Usuario')
    rol = models.CharField(max_length=20, choices=ROL_PARTICIPANTE, default='responsable', verbose_name='Rol')
    respuesta = models.CharField(max_length=20, choices=RESPUESTA_INVITACION, default='pendiente', verbose_name='Respuesta')

    def __str__(self):
        return f'{self.usuario} · {self.get_rol_display()}'

    class Meta:
        verbose_name = 'Participante'
        verbose_name_plural = 'Participantes'
        constraints = [
            models.UniqueConstraint(fields=['cita', 'usuario'], name='participante_cita_unico', condition=Q(status=True)),
        ]


class CierreCita(ModeloBase):
    cita = models.OneToOneField(Cita, on_delete=models.PROTECT, related_name='cierre', verbose_name='Cita')
    resumen = models.TextField(blank=True, default='', verbose_name='Resumen')
    pidio_proforma = models.BooleanField(default=False, verbose_name='¿Pidió proforma?')
    fue_soporte = models.BooleanField(default=False, verbose_name='¿Fue soporte de la plataforma?')
    es_lead = models.BooleanField(default=False, verbose_name='¿Es un lead potencial?')
    asistio = models.BooleanField(default=True, verbose_name='¿El cliente asistió?')
    tipo_reunion = models.CharField(max_length=20, choices=TIPO_REUNION, default='otro', verbose_name='Tipo de reunión')
    registrado_por = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='cierres_registrados',
                                       verbose_name='Registrado por')

    def __str__(self):
        return f'Cierre de {self.cita}'

    class Meta:
        verbose_name = 'Cierre de cita'
        verbose_name_plural = 'Cierres de cita'


class NotaCita(ModeloBase):
    cita = models.OneToOneField(Cita, on_delete=models.PROTECT, related_name='nota', verbose_name='Cita')
    texto = models.TextField(blank=True, default='', verbose_name='Notas')

    def __str__(self):
        return f'Notas de {self.cita}'

    class Meta:
        verbose_name = 'Nota de cita'
        verbose_name_plural = 'Notas de cita'


class BloqueOcupado(ModeloBase):
    """Ocupación consolidada por usuario. La base garantiza que dos bloques activos de la misma
    persona no se solapen (restricción de exclusión): es la guarda contra la doble asignación."""
    usuario = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bloques_ocupados',
                                verbose_name='Usuario')
    inicio = models.DateTimeField(verbose_name='Inicio')
    fin = models.DateTimeField(verbose_name='Fin')
    fuente = models.CharField(max_length=20, choices=FUENTE_BLOQUEO, default='cita', verbose_name='Fuente')
    cita = models.ForeignKey(Cita, on_delete=models.PROTECT, blank=True, null=True, related_name='bloques',
                             verbose_name='Cita')
    referencia = models.CharField(max_length=255, blank=True, default='', verbose_name='Referencia externa')

    def __str__(self):
        return f'{self.usuario} · {self.inicio:%d/%m %H:%M}-{self.fin:%H:%M}'

    class Meta:
        verbose_name = 'Bloque ocupado'
        verbose_name_plural = 'Bloques ocupados'
        ordering = ('inicio',)
        constraints = [
            models.CheckConstraint(condition=Q(fin__gt=F('inicio')), name='bloque_rango_valido'),
            ExclusionConstraint(
                name='bloque_sin_solapamiento',
                expressions=[(TsTzRange('inicio', 'fin', RangeBoundary()), RangeOperators.OVERLAPS),
                             ('usuario', RangeOperators.EQUAL)],
                condition=Q(status=True),
            ),
        ]


class ActividadCita(RegistroInmutable):
    """Línea de actividad de la cita: se escribe una vez y nunca se edita ni se borra."""
    cita = models.ForeignKey(Cita, on_delete=models.PROTECT, related_name='actividad', verbose_name='Cita')
    accion = models.CharField(max_length=60, verbose_name='Acción')
    detalle = models.CharField(max_length=300, blank=True, default='', verbose_name='Detalle')
    autor = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, blank=True, null=True,
                              related_name='actividad_citas', verbose_name='Autor')
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')

    def __str__(self):
        return f'{self.creado_en:%d/%m %H:%M} · {self.accion}'

    class Meta:
        verbose_name = 'Actividad de cita'
        verbose_name_plural = 'Actividad de citas'
        ordering = ('creado_en',)


class EnvioRecordatorio(RegistroInmutable):
    """Evidencia de cada recordatorio enviado; la unicidad (cita, tipo) impide enviarlo dos veces."""
    cita = models.ForeignKey(Cita, on_delete=models.PROTECT, related_name='recordatorios', verbose_name='Cita')
    tipo = models.CharField(max_length=20, verbose_name='Tipo')
    enviado_en = models.DateTimeField(auto_now_add=True, verbose_name='Enviado')
    exito = models.BooleanField(default=True, verbose_name='Enviado con éxito')
    detalle = models.CharField(max_length=300, blank=True, default='', verbose_name='Detalle')

    def __str__(self):
        return f'{self.cita} · {self.tipo}'

    class Meta:
        verbose_name = 'Envío de recordatorio'
        verbose_name_plural = 'Envíos de recordatorio'
        constraints = [
            models.UniqueConstraint(fields=['cita', 'tipo'], name='recordatorio_unico_por_cita'),
        ]


TIPO_TOKEN = (
    ('cita', 'Gestión de una cita'),
    ('cliente', 'Enlace personal del cliente'),
)


class TokenAcceso(ModeloBase):
    """Enlace sin contraseña para el cliente. Solo se guarda el hash del token; el token en claro
    viaja una vez por correo. Vence, cuenta usos y se puede revocar."""
    tipo = models.CharField(max_length=20, choices=TIPO_TOKEN, verbose_name='Tipo')
    token_hash = models.CharField(max_length=64, verbose_name='Hash del token')
    cita = models.ForeignKey(Cita, on_delete=models.PROTECT, blank=True, null=True, related_name='tokens',
                             verbose_name='Cita')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, blank=True, null=True, related_name='tokens',
                                verbose_name='Cliente')
    vence = models.DateTimeField(verbose_name='Vence')
    ultimo_uso = models.DateTimeField(blank=True, null=True, verbose_name='Último uso')
    usos = models.PositiveIntegerField(default=0, verbose_name='Usos')
    revocado = models.BooleanField(default=False, verbose_name='Revocado')

    def __str__(self):
        return f'{self.get_tipo_display()} · {self.cita or self.cliente}'

    class Meta:
        verbose_name = 'Token de acceso'
        verbose_name_plural = 'Tokens de acceso'
        ordering = ('-fecha_registro',)
        constraints = [
            models.UniqueConstraint(fields=['token_hash'], name='token_acceso_hash_unico'),
        ]
        indexes = [models.Index(fields=['token_hash'], name='token_acceso_hash_idx')]


class PreferenciaAgenda(ModeloBase):
    """Preferencias personales de alertas y la marca de «primer ingreso» visto."""
    usuario = models.OneToOneField(AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='preferencia_agenda',
                                   verbose_name='Usuario')
    aviso_previo_min = models.PositiveSmallIntegerField(default=10, verbose_name='Avisar antes de la cita (min)')
    alerta_pantalla = models.BooleanField(default=True, verbose_name='Alerta en pantalla')
    alerta_push = models.BooleanField(default=True, verbose_name='Notificación push')
    alerta_correo = models.BooleanField(default=False, verbose_name='Correo al asignarme una cita')
    primer_ingreso_visto = models.BooleanField(default=False, verbose_name='Guía de primer ingreso vista')

    def __str__(self):
        return f'Preferencias de {self.usuario}'

    class Meta:
        verbose_name = 'Preferencia de agenda'
        verbose_name_plural = 'Preferencias de agenda'


class CapturaTecnica(ModeloBase):
    """Datos técnicos del navegador con que el cliente reservó (abuso y soporte). La IP completa se
    anonimiza pasado `cliente_conservar_ip_dias` (cron `mantenimiento_agenda`)."""
    cita = models.ForeignKey(Cita, on_delete=models.PROTECT, blank=True, null=True, related_name='capturas',
                             verbose_name='Cita')
    solicitud = models.ForeignKey(Solicitud, on_delete=models.PROTECT, blank=True, null=True, related_name='capturas',
                                  verbose_name='Solicitud')
    ip = models.CharField(max_length=64, blank=True, default='', verbose_name='IP')
    navegador = models.CharField(max_length=300, blank=True, default='', verbose_name='Navegador')
    origen = models.CharField(max_length=300, blank=True, default='', verbose_name='Página de origen')
    idioma_navegador = models.CharField(max_length=40, blank=True, default='', verbose_name='Idioma del navegador')
    anonimizada = models.BooleanField(default=False, verbose_name='IP anonimizada')

    def __str__(self):
        return f'Captura de {self.cita or self.solicitud}'

    class Meta:
        verbose_name = 'Captura técnica'
        verbose_name_plural = 'Capturas técnicas'


class TextoPortal(ModeloBase):
    """Textos visibles del portal público en los tres idiomas. Se cargan con
    `scripts/seed_textos_portal.py`; el equipo puede ajustarlos sin tocar código."""
    clave = models.CharField(max_length=60, verbose_name='Clave')
    es = models.TextField(verbose_name='Español')
    en = models.TextField(blank=True, default='', verbose_name='Inglés')
    pt = models.TextField(blank=True, default='', verbose_name='Portugués')

    CACHE_CLAVE = 'agenda:textos_portal:{}'

    def __str__(self):
        return self.clave

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.limpiar_cache()

    def delete(self, *args, **kwargs):
        resultado = super().delete(*args, **kwargs)
        self.limpiar_cache()
        return resultado

    @classmethod
    def limpiar_cache(cls):
        from django.core.cache import cache
        cache.delete_many([cls.CACHE_CLAVE.format(idioma) for idioma in ('es', 'en', 'pt')])

    class Meta:
        verbose_name = 'Texto del portal'
        verbose_name_plural = 'Textos del portal'
        ordering = ('clave',)
        constraints = [models.UniqueConstraint(fields=['clave'], name='texto_portal_clave_unica')]


CANAL_AVISO = (
    ('correo', 'Correo'),
    ('push', 'Notificación push'),
)


class AvisoProximo(RegistroInmutable):
    """Evidencia del aviso «empieza en 10 minutos» por usuario y canal; la unicidad impide repetirlo."""
    cita = models.ForeignKey(Cita, on_delete=models.PROTECT, blank=True, null=True, related_name='avisos_proximos',
                             verbose_name='Cita')
    reunion = models.ForeignKey(Reunion, on_delete=models.PROTECT, blank=True, null=True,
                                related_name='avisos_proximos', verbose_name='Reunión')
    usuario = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='avisos_proximos',
                                verbose_name='Usuario')
    canal = models.CharField(max_length=10, choices=CANAL_AVISO, verbose_name='Canal')
    enviado_en = models.DateTimeField(auto_now_add=True, verbose_name='Enviado')
    exito = models.BooleanField(default=True, verbose_name='Enviado con éxito')
    detalle = models.CharField(max_length=300, blank=True, default='', verbose_name='Detalle')

    def __str__(self):
        return f'{self.cita or self.reunion} · {self.usuario} · {self.canal}'

    class Meta:
        verbose_name = 'Aviso de inicio próximo'
        verbose_name_plural = 'Avisos de inicio próximo'
        constraints = [
            models.UniqueConstraint(fields=['cita', 'usuario', 'canal'], name='aviso_proximo_cita_unico',
                                    condition=Q(cita__isnull=False)),
            models.UniqueConstraint(fields=['reunion', 'usuario', 'canal'], name='aviso_proximo_reunion_unico',
                                    condition=Q(reunion__isnull=False)),
            models.CheckConstraint(condition=Q(cita__isnull=False) | Q(reunion__isnull=False),
                                   name='aviso_proximo_con_origen'),
        ]
