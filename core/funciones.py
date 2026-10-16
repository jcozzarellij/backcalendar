import json
from datetime import date, datetime, time, timedelta

from django.contrib.admin.models import DELETION, ADDITION, CHANGE, LogEntry
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage
from django.core import signing
from django.db import models
from django.db.models import Value, F, QuerySet
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.utils.safestring import mark_safe

from autenticacion.models import Usuario
from seguridad.models import Configuracion, CronLogEjecucion, GroupModulo, Modulo, ModuloGrupo
from .constantes import NOMBRE_MONEDA, SIMBOLO_MONEDA


unicode = str


def remover_caracteres_especiales_unicode(cadena):
    return cadena.replace(u'ñ', u'n').replace(u'Ñ', u'N').replace(u'Á', u'A').replace(u'á', u'a').replace(u'É',
                                                                                                          u'E').replace(
        u'é', u'e').replace(u'Í', u'I').replace(u'í', u'i').replace(u'Ó', u'O').replace(u'ó', u'o').replace(u'Ú',
                                                                                                            u'U').replace(
        u'ú', u'u').replace(u'ü', u'u').replace(u'Ü', u'U').replace(u'°', u'_').replace(u'º', u'_').replace('[',
                                                                                                            '').replace(
        ']', '').replace('{', '').replace('}', '').replace('-', '')


def convertir_fecha(s):
    if ':' in s:
        sep = ':'
    elif '-' in s:
        sep = '-'
    else:
        sep = '/'
    return date(int(s.split(sep)[2]), int(s.split(sep)[1]), int(s.split(sep)[0]))


def paginador(request, list_qs, cantidad, data, url_vars=''):
    """
    Paginación optimizada que cambia su comportamiento basado en el volumen de datos.
    Para consultas pesadas (>10K registros) solo muestra anterior/siguiente.
    """
    UMBRAL_CONSULTA_PESADA = 10000

    if cantidad <= 0:
        cantidad = 1

    try:
        page_number = max(1, int(request.GET.get('page', 1)))
    except (TypeError, ValueError):
        page_number = 1

    # Obtener total y verificar si es una consulta pesada
    is_queryset = isinstance(list_qs, QuerySet)

    if is_queryset:
        total_query = list_qs.count()
        if total_query == 0:
            return _empty_response(data)
    else:
        total_query = len(list_qs)
        if total_query == 0:
            return _empty_response(data)

    is_heavy_query = total_query > UMBRAL_CONSULTA_PESADA
    page_number = min(page_number, (total_query + cantidad - 1) // cantidad)
    offset = (page_number - 1) * cantidad

    # Obtener registros de la página actual
    end_index = min(offset + cantidad, total_query)
    paginated_qs = list_qs[offset:end_index]

    # Verificar si hay página siguiente
    has_next = total_query > (offset + cantidad)
    has_previous = page_number > 1

    # Calcular desde y hasta
    desde = offset + 1 if paginated_qs else 0
    hasta = offset + len(paginated_qs)

    # Estructura de página
    class PageLike:
        def __init__(self, object_list, number, has_next, has_previous):
            self.object_list = object_list
            self.number = number
            self._has_next = has_next
            self._has_previous = has_previous

        def has_next(self):
            return self._has_next

        def has_previous(self):
            return self._has_previous

        def next_page_number(self):
            return self.number + 1 if self._has_next else None

    page = PageLike(
        object_list=paginated_qs,
        number=page_number,
        has_next=has_next,
        has_previous=has_previous
    )

    # Estructura de paginación
    if is_heavy_query:
        paging = {
            'total': total_query,
            'desde': desde,
            'hasta': hasta,
            'is_heavy_query': True,
            'paginas': [],
            'primera_pagina': False,
            'ultima_pagina': False
        }
    else:
        num_pages = (total_query + cantidad - 1) // cantidad
        rango = 5
        left = max(1, page_number - rango)
        right = min(num_pages, page_number + rango)

        paging = {
            'num_pages': num_pages,
            'paginas': list(range(left, right + 1)),
            'primera_pagina': left > 1,
            'ultima_pagina': right < num_pages,
            'ellipsis_izquierda': left - 1,
            'ellipsis_derecha': right + 1,
            'total': total_query,
            'desde': desde,
            'hasta': hasta,
            'is_heavy_query': False
        }

    # Actualizar data
    data.update({
        'page': page,
        'paging': paging,
        'listado': paginated_qs,
        'pageHasNext': has_next,
        'pageNextPag': page_number + 1 if has_next else 0,
        'dataJsonPaginacion': json.dumps({
            "hasNext": has_next,
            "nextPag": page_number + 1 if has_next else 0
        })
    })

    if "page=" not in url_vars:
        url_vars += f"&page={page_number}"

    return data


def _empty_response(data):
    """Helper function para manejar respuestas vacías"""
    data.update({
        'page': EmptyPage,
        'paging': {
            'paginas': [],
            'primera_pagina': False,
            'ultima_pagina': False,
            'total': 0,
            'desde': 0,
            'hasta': 0,
            'is_heavy_query': False
        },
        'listado': [],
        'pageHasNext': False,
        'pageNextPag': 0,
        'dataJsonPaginacion': json.dumps({"hasNext": False, "nextPag": 0})
    })
    return data


def get_filtros_anteriores(request, data, url_vars, en_paginador: bool = False):
    data["dict_url_vars"] = ""
    if en_paginador:
        if url_vars:
            try:
                dict_url_vars = json.loads(get_decrypt(request.GET.get('dict_url_vars'))[1]) if request.GET.get(
                    'dict_url_vars') else {}
                dict_url_vars[request.path] = url_vars
                d = json.dumps(dict_url_vars)
                data["dict_url_vars"] = "dict_url_vars={}".format(get_encrypt(d)[1])
            except Exception as ex:
                print(ex)
    elif request.GET.get("dict_url_vars"):
        data["dict_url_vars"] = "dict_url_vars={}".format(
            request.GET.get("dict_url_vars", "").replace("dict_url_vars=", ""))


def obtener_perfil_activo(request):
    """Perfil activo en la sesión: la plataforma tiene un solo perfil ('administrativo'), que es
    cualquier usuario activo con acceso al panel (staff o superusuario). None si no aplica."""
    if not request.user.is_authenticated:
        return None
    nuevo = 'administrativo' if request.user.es_administrativo() else None
    request.session['perfil_activo'] = nuevo
    return nuevo


def secure_module(f):
    from django.contrib import messages
    def new_f(*args, **kwargs):
        request = args[0]
        if request.user.is_superuser:
            return f(*args, **kwargs)
        if request.user.is_authenticated and request.user.is_staff:
            try:
                urls_validas = ['perfilpanel', 'panel']
                if request.path.replace('/', '') in urls_validas:
                    return f(*args, **kwargs)
                modulos_id = list(
                    GroupModulo.objects.filter(group__in=request.user.groups.all(), status=True).values_list('modulos__id',
                                                                                                flat=True))
                ms = Modulo.objects.filter(
                    status=True, id__in=modulos_id,
                ).annotate(
                    url_2=Value(request.path, output_field=models.CharField()))
                if ms.filter(url_2__istartswith=F('url')).exists():
                    return f(*args, **kwargs)
                else:
                    messages.error(request, "No tienes acceso.")
                    return HttpResponseRedirect("/panel/")
            except Exception as ex:
                print(ex)
                if request.user.is_superuser:
                    messages.error(request, 'Método: {}, Error: {}'.format(request.method, str(ex)))
                return HttpResponseRedirect("/")
        else:
            return HttpResponseRedirect("/")

    return new_f


def solo_administrador(f):
    """Candado de defensa en profundidad para pantallas GLOBALES de plataforma (muestran u
    operan datos de TODOS los clientes: RAG admin, logs de herramientas, plantillas, etc.).
    Complementa a @secure_module: aunque el módulo se asigne por error al grupo de un
    cliente, la vista exige superusuario o pertenecer al grupo administrador."""
    from django.contrib import messages

    def new_f(*args, **kwargs):
        request = args[0]
        from backcalendar.settings import ID_GRUPO_ADMINISTRADOR
        es_admin = request.user.is_authenticated and (
            request.user.is_superuser
            or request.user.groups.filter(pk=ID_GRUPO_ADMINISTRADOR).exists()
        )
        if not es_admin:
            messages.error(request, 'Esta pantalla es exclusiva del administrador de la plataforma.')
            return HttpResponseRedirect('/panel/')
        return f(*args, **kwargs)

    return new_f


def generar_nombre(nombre, original):
    from django.utils.text import slugify
    ext = ""
    if original.find(".") > 0:
        ext = original[original.rfind("."):]
    return slugify("{} {}".format(nombre, datetime.now().strftime("%Y-%m-%d %H-%M"))) + ext.lower()


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def custom_get_timezone(request, user=None):
    import pytz
    from backcalendar.settings import TIME_ZONE
    if request.user.is_authenticated:
        return timezone.now().astimezone(pytz.timezone(TIME_ZONE))
    return timezone.now().astimezone(pytz.timezone(TIME_ZONE))


def addData(request, data):
    # Abrir la publickey para encriptar
    from backcalendar import settings
    from backcalendar.settings import URL_GENERAL
    from django.utils import timezone
    data['remotenameaddr'] = '%s' % (request.META['SERVER_NAME'])
    data['server_response'] = SERVER_RESPONSE = '207'
    data["URL_GENERAL"] = URL_GENERAL
    data['version_css'] = settings.VERSION_CSS
    data["campos_no_mostrados"] = []
    data["full_url"] = full_url = request.path + "?" + "&".join(["{}={}".format(k, v) for k, v in request.GET.items()])
    data["full_url_hash"] = get_encrypt(full_url)[1]
    confi = Configuracion.get_instancia()
    hoy = custom_get_timezone(request)
    hora_actual = hoy.time()
    # WEB PUSH
    webpush_settings = getattr(settings, 'WEBPUSH_SETTINGS', {})
    # ------FILTRO HECHOS EN LOS LISTADOS
    data['dict_url_vars_input'] = mark_safe(
        '<input type="hidden" name="dict_url_vars" id="id_dict_url_vars" value="{}" />'.format(
            request.GET.get('dict_url_vars') or ""))
    if request.GET.get('dict_url_vars'):
        try:
            dict_url_vars_completo = request.GET.get('dict_url_vars') or "{}"
            dict_url_vars_completo = json.loads(get_decrypt(dict_url_vars_completo)[1])
            data['dict_url_vars_completo'] = dict_url_vars_completo.get(request.path) or ""
        except Exception as ex:
            print(ex)
    # -.---WEB PUSH----
    data['fecha_actual'] = hoy.date()
    data['other_action'] = request.GET.get('other-action')
    data['hoy'] = hoy.strftime('%d/%M/%Y %H:%m')
    data['dominio_reunion'] = 'meet.jit.si'
    data['confi'] = confi
    data['favicon'] = confi.ico.url if confi.ico else ""
    data['logo'] = confi.logo_sistema.url if confi.logo_sistema else ""
    data['nombreempresa'] = confi.nombre_empresa
    data['telefonoempresa'] = confi.telefono if confi.telefono else ''
    data['alias'] = confi.alias
    data['NOMBRE_MONEDA'] = NOMBRE_MONEDA
    data['SIMBOLO_MONEDA'] = SIMBOLO_MONEDA
    data["DOMINIO_DEL_SISTEMA"] = request.build_absolute_uri('/')[:-1].strip("/")
    data['hora_actual'] = hora_actual
    data['hoy'] = datetime.now().date()
    data['hoy_str'] = str(datetime.now().date())
    # El botón "Regresar a mi sesión" sale si hay respaldo en la sesión O en la cookie
    # firmada (la sesión se recambia en cada logout/login y a veces pierde la marca;
    # la cookie sobrevive — ver seguridad/cambiar_sesion_view.py).
    if 'user_anterior' in request.session:
        data["sesion_anterior"] = True
    else:
        from seguridad.cambiar_sesion_view import _leer_cookie_regreso
        if request.user.is_authenticated and _leer_cookie_regreso(request):
            data["sesion_anterior"] = True
    if request.user.is_authenticated:
        # Notificaciones para el dropdown del topbar (base.html). Sin esto el
        # popup queda siempre vacío. Mostramos las 5 últimas no leídas y el
        # total no leído para el badge.
        try:
            from seguridad.models import Notificacion as _Notif
            _qs_not = _Notif.objects.filter(
                destinatario=request.user, leido=False, status=True,
            ).order_by('-fecha_registro')
            data['totalnot'] = _qs_not.count()
            data['listnotification'] = list(_qs_not[:5])
        except Exception:
            data['totalnot'] = 0
            data['listnotification'] = []
        if request.user.cambio_clave and request.path != '/changepass/':
            data['activar_cambio_clave'] = request.user.cambio_clave
        get_filtros_anteriores(request, data, None)
        data["fecha_session_expira"] = (request.session.model.objects.get(
            pk=request.session.session_key).expire_date - timezone.now()).seconds
        if not request.session.exists(request.session.session_key):
            request.session.create()
        data['ruta_val'] = request.path
        perfil_activo = obtener_perfil_activo(request)
        data['perfil_activo'] = perfil_activo
        data.setdefault('ocultar_sidebar', False)
        if perfil_activo:
            data['gruposUserLogueado'] = ", ".join(list(request.user.groups.all().values_list('name', flat=True)))
            if request.user.is_superuser:
                modulos_qs = Modulo.objects.filter(status=True)
            else:
                modulos_id_rol = GroupModulo.objects.filter(
                    group__in=request.user.groups.all(), status=True,
                ).values_list('modulos__id', flat=True)
                modulos_qs = Modulo.objects.filter(id__in=modulos_id_rol, status=True)
            data["modulos_id"] = modulos_id = list(modulos_qs.values_list('id', flat=True))
            data['grupos'] = ModuloGrupo.objects.filter(
                status=True, modulos__id__in=modulos_id,
            ).order_by('prioridad').distinct()
            modulos = Modulo.objects.annotate(url_2=Value(request.path, output_field=models.CharField())).filter(
                url_2__istartswith=F('url'))
            if modulos.exists():
                if data['grupos'].filter(modulos__in=modulos, status=True).exists():
                    data["group"] = data['grupos'].filter(modulos__in=modulos, status=True).first().nombre
            if 'ruta_lista' not in request.session:
                request.session['ruta_lista'] = [['/panel/', 'Inicio']]
            rutalista = request.session['ruta_lista']
            if request.path and request.method == 'GET':
                if Modulo.objects.values('url').filter(url=request.path).exists():
                    modulo = Modulo.objects.values("url", "nombre").filter(url=request.path).first()
                    url = [modulo['url'], modulo['nombre']]
                    if rutalista.count(url) <= 0:
                        if rutalista.__len__() >= 4:
                            b = rutalista[1]
                            rutalista.remove(b)
                            rutalista.append(url)
                        else:
                            rutalista.append(url)
                    request.session['ruta_lista'] = rutalista
                    data["url_back"] = '/'
                    url_back = [data['url_back']]
                    request.session['url_back'] = url_back
            data["ruta_lista"] = rutalista


def redirectAfterPostGet(request):
    dict_url_vars = request.GET.get('dict_url_vars') or request.POST.get('dict_url_vars') or ""
    if dict_url_vars:
        try:
            dict_url_vars = json.loads(get_decrypt(dict_url_vars)[1]).get(request.path) or ""
        except Exception as ex:
            print(ex)
    salida = "?action=add&" if '_add' in request.POST else request.path + "?"
    return salida + "{}".format(dict_url_vars)


class MiPaginador(Paginator):
    def __init__(self, object_list, per_page, orphans=0, allow_empty_first_page=True, rango=5):
        super(MiPaginador, self).__init__(object_list, per_page, orphans=orphans,
                                          allow_empty_first_page=allow_empty_first_page)
        self.rango = rango
        self.paginas = []
        self.primera_pagina = False
        self.ultima_pagina = False
        self.total = object_list.count()
        self.desde = 0
        self.hasta = 0

    def rangos_paginado(self, pagina):
        left = pagina - self.rango
        right = pagina + self.rango
        if left < 1:
            left = 1
        if right > self.num_pages:
            right = self.num_pages
        self.paginas = range(left, right + 1)
        self.primera_pagina = True if left > 1 else False
        self.ultima_pagina = True if right < self.num_pages else False
        self.ellipsis_izquierda = left - 1
        self.ellipsis_derecha = right + 1


def get_encrypt(values, compress=True):
    """Firma `values` con Django signing. `compress=True` (default) reduce el largo pero Django
    antepone '.' al token cuando comprime — y un token que viaja por URL que empiece con '.' lo
    bloquea nginx con 403 por la regla anti-dotfiles (.git/.env). Para esos casos pasar
    `compress=False` (nunca empieza con '.'). `get_decrypt` (signing.loads) lee ambos formatos."""
    try:
        return True, signing.dumps(values, compress=compress)
    except Exception as ex:
        return False, str(ex)


def get_decrypt(cyphertxt, max_age=None):
    """Deshace un token de get_encrypt. `max_age` (segundos) hace EXPIRAR el token:
    obligatorio para tokens que viajan por URL a terceros — sin expiración, un enlace filtrado
    daba acceso permanente. Los tokens persistidos internamente siguen sin max_age."""
    try:
        return True, signing.loads(cyphertxt, max_age=max_age)
    except Exception as ex:
        return False, str(ex)


# --- Identificadores opacos para URLs (firmados, no cifrado fuerte) ---

def encrypt_sesion_id(pk):
    """Devuelve un token opaco a partir de un id entero. Uso en links /?sesion=<token>."""
    if pk in (None, ''):
        return ''
    ok, token = get_encrypt(int(pk))
    return token if ok else ''


def decrypt_sesion_id(token, default=None):
    """Inversa de encrypt_sesion_id. Si el token no parece firmado, intenta int() directo
    (tolerante con tabs abiertas / links viejos en claro)."""
    if token in (None, ''):
        return default
    if isinstance(token, int):
        return token
    ok, valor = get_decrypt(token)
    if ok:
        try:
            return int(valor)
        except (TypeError, ValueError):
            return default
    # Fallback: id crudo
    try:
        return int(token)
    except (TypeError, ValueError):
        return default


WA_SESION_ACTIVA_KEY = 'wa_sesion_id'


_TABLAS_EXISTENTES_CACHE = set()


def db_table_exists(table):
    # Memo: `get_table_list` ENUMERA TODO el esquema en cada llamada, y esto se invoca en el hot
    # path de ParametroSistema.valor_de (por cada param, en cada expiración de su cache de 60s, en
    # cada worker) → ráfaga de introspecciones caras al Postgres. Una tabla que EXISTE no
    # desaparece en runtime, así que se cachea el True de por vida del proceso. El False NO se
    # cachea: una migración puede crear la tabla mientras el worker vive, y así se detecta igual.
    if table in _TABLAS_EXISTENTES_CACHE:
        return True
    try:
        from django.db import connection
        cursor = connection.cursor()
        table_names = [x.name for x in list(connection.introspection.get_table_list(cursor))]
    except Exception as ex:
        print("unable to determine if the table '%s' exists" % table)
    else:
        existe = table in table_names
        if existe:
            _TABLAS_EXISTENTES_CACHE.add(table)
        return existe


def salva_auditoria(request, model, action, nombre, qs_nuevo=None, qs_anterior=None):
    from seguridad.models import AudiUsuarioTabla
    import json
    arr = []
    anterior = {}
    nuevo = {}
    if qs_anterior:
        anterior["fields"] = {}
        for x in qs_anterior:
            for k, v in x.items():
                anterior["fields"][k] = str(v)
        anterior["pk"] = qs_anterior[0]["id"]
        anterior["fields"]["__ff_detalle_ff__"] = "ANTERIOR"
        anterior["model"] = "{}.{}".format(model._meta.app_label, model._meta.model_name)
        arr.append(anterior)
    if qs_nuevo:
        nuevo["fields"] = {}
        for x in qs_nuevo:
            for k, v in x.items():
                nuevo["fields"][k] = str(v)
        nuevo["pk"] = qs_nuevo[0]["id"]
        nuevo["fields"]["__ff_detalle_ff__"] = "NUEVO"
        nuevo["model"] = "{}.{}".format(model._meta.app_label, model._meta.model_name)
        arr.append(nuevo)
    data_json = json.dumps(arr)
    user = request.user
    auditusuariotabla = AudiUsuarioTabla(usuario_id=user.id,
                                         modelo=model,
                                         registroname=nombre,
                                         accion=action,
                                         datos_json=data_json,
                                         ip=str(request.ipAdd))
    if 'user_anterior' in request.session:
        auditusuariotabla.usuario_admin_id = int(request.session['user_anterior'])
    auditusuariotabla.save()


def codnombre(nombres, apellidos, user_pk=0):
    lnombres = nombres.split(' ')
    lapellidos = apellidos.split(' ')
    codnombre = "{}{}".format(lnombres[0].lower()[0], str(lapellidos[0].lower()))
    # Sin `status`: el username es único en toda la tabla, así que un usuario dado de baja
    # sigue ocupando el suyo. Filtrar acá generaría uno que choca al guardar.
    if Usuario.objects.filter(username__icontains=codnombre).exclude(pk=user_pk).exists():
        count2 = Usuario.objects.filter(username__icontains=codnombre).count() + 1
        codnombre = "{}{}{}".format(lnombres[0].lower()[0], str(lapellidos[0].lower()), count2)
    return codnombre


def log(mensaje, request, accion, user=None, obj=None):
    if accion == "del":
        logaction = DELETION
    elif accion == "add":
        logaction = ADDITION
    else:
        logaction = CHANGE
    LogEntry.objects.log_action(
        user_id=request.user.id if not user else user.id,
        content_type_id=None,
        object_id=obj,
        object_repr='',
        action_flag=logaction,
        change_message=unicode(mensaje))


def logCron(proceso, detalle, exito=False):
    # Obtiene la fecha y hora actuales
    ahora = timezone.now()

    # Calcula el tiempo límite de las últimas 3 horas
    hace_tres_horas = ahora - timedelta(hours=3)

    # Verifica si ya existe un registro con el mismo proceso, detalle y en las últimas 3 horas
    existe_log = CronLogEjecucion.objects.filter(
        proceso=proceso,
        detalle=detalle,
        fecha=ahora.date(),
        hora__gte=hace_tres_horas.time()  # Hora mayor o igual al límite de 3 horas atrás
    ).exists()

    # Solo crea el registro si no existe uno igual en las últimas 3 horas
    if not existe_log:
        CronLogEjecucion.objects.create(
            proceso=proceso,
            detalle=detalle,
            conexito=exito
        )
        # Aviso por correo solo ante fallo (y solo cuando es un log nuevo, así la
        # deduplicación de 3h evita spam). No agrega crons: es event-driven.
        if not exito:
            _notificar_fallo_cron(proceso, detalle)


def _notificar_fallo_cron(proceso, detalle):
    """Manda un correo a los responsables cuando un proceso/cron falla.
    Best-effort: si el correo falla, no rompe el logueo del cron."""
    try:
        from django.conf import settings
        from django.core.mail import send_mail
        destinatarios = getattr(settings, 'ERROR_NOTIFY_EMAILS', []) or []
        if not destinatarios:
            return
        asunto = f'[backcalendar] Falló el proceso: {proceso}'
        cuerpo = (
            f'El proceso "{proceso}" reportó un fallo.\n\n'
            f'Detalle:\n{detalle}\n\n'
            f'Fecha: {timezone.now():%Y-%m-%d %H:%M}\n\n'
            f'Aviso automático. Se deduplica: máximo 1 correo cada 3h por el mismo error.'
        )
        send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, destinatarios, fail_silently=True)
    except Exception:
        pass


def notificacion(titulo, cuerpo, destinatario, url, prioridad, tipo=1, request=None):
    from seguridad.models import Notificacion
    notificacion = Notificacion(titulo=titulo, cuerpo=cuerpo,
                                destinatario=destinatario, url=url,
                                prioridad=prioridad,
                                tipo=tipo,
                                fecha_hora_visible=datetime.now() + timedelta(days=1))
    if request:
        notificacion.save(request)
    else:
        notificacion.save()

# Contador de respaldo EN MEMORIA del proceso, para cuando el cache no responde (`cache.add`
# devuelve None). El tope sigue existiendo aunque sea por worker. Se limpia solo al vencer.
import logging as _rl_logging
import threading as _rl_threading
import time as _rl_time

_RATE_MEMORIA = {}
_RATE_MEMORIA_LOCK = _rl_threading.Lock()
_RATE_MEMORIA_TOPE = 20000
_RATE_AVISO = [0.0]


def _rate_limit_en_memoria(key, limit, seconds):
    """True si `key` ya superó `limit` en la ventana actual, contando solo en este proceso."""
    ahora = _rl_time.time()
    with _RATE_MEMORIA_LOCK:
        if len(_RATE_MEMORIA) > _RATE_MEMORIA_TOPE:
            # Poda defensiva: sin esto, una avalancha de IPs distintas haría
            # crecer el diccionario sin techo dentro del worker web.
            for k, (_, vence) in list(_RATE_MEMORIA.items()):
                if vence <= ahora:
                    _RATE_MEMORIA.pop(k, None)
            if len(_RATE_MEMORIA) > _RATE_MEMORIA_TOPE:
                _RATE_MEMORIA.clear()
        cuenta, vence = _RATE_MEMORIA.get(key, (0, 0))
        if vence <= ahora:
            cuenta, vence = 0, ahora + seconds
        cuenta += 1
        _RATE_MEMORIA[key] = (cuenta, vence)
    return cuenta > limit


def _contar(key, limit, seconds):
    """True si `key` superó `limit` en la ventana. Cae al contador en memoria si el cache calla."""
    creada = cache.add(key, 1, timeout=seconds)
    if creada is None:
        return None
    if creada:
        return False
    try:
        actual = cache.incr(key)
    except ValueError:
        # La clave venció entre el add y el incr: arranca ventana nueva.
        cache.set(key, 1, timeout=seconds)
        actual = 1
    if actual is None:
        return None
    return actual > limit


def rate_limit(limit=10, seconds=60, techo_ip=None):
    # La clave incluye la vista: cada endpoint tiene SU contador con SU límite. Con la
    # clave global por IP, una vista de alto volumen agotaba el límite de vistas chicas y
    # devolvía 429 cruzados.
    #
    # `techo_ip` es un SEGUNDO contador por IP real que corre ADEMÁS del de Bearer: keyear por
    # Bearer se esquiva mandando un token distinto en cada request. Apagado por defecto.
    import functools
    import hashlib

    tope_ip = techo_ip

    def _apply(view_func):
        nombre = getattr(view_func, "__name__", "view")

        @functools.wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            # Identidad de negocio, no la IP del balanceador (detrás de nginx con uwsgi_pass,
            # REMOTE_ADDR es siempre el LB → un único contador global para toda la plataforma, y
            # un solo cliente dejaba a todos en 429). Con Bearer keyeamos por conexión; sin él,
            # por la IP real del cliente (X-Forwarded-For).
            auth = request.headers.get("Authorization") or ""
            if auth.startswith("Bearer "):
                ident = "cx:" + hashlib.sha256(auth[7:].strip().encode()).hexdigest()[:16]
            else:
                ident = "ip:" + (get_client_ip(request) or request.META.get("REMOTE_ADDR") or "?")
            ip = get_client_ip(request) or request.META.get("REMOTE_ADDR") or "?"

            # Incremento cuasi-atómico: add fija el TTL al crear; si ya existe, incr sobre el
            # mismo valor evita la carrera get-then-set de N requests concurrentes.
            # _contar devuelve True (excedido), False (dentro) o None (el cache no respondió).
            tope_base = limit() if callable(limit) else limit
            controles = [(f"rate:{nombre}:{ident}", tope_base)] if tope_base and tope_base > 0 else []
            if tope_ip and ident.startswith("cx:"):
                controles.append((f"rate:{nombre}:ip:{ip}", tope_ip))

            excedido = False
            for key, tope in controles:
                res = _contar(key, tope, seconds)
                if res is None:
                    # Un aviso por minuto: con el cache caído esto se dispara en CADA request y el
                    # log se volvería inservible justo cuando hay que leerlo.
                    ahora = _rl_time.time()
                    if ahora - _RATE_AVISO[0] > 60:
                        _RATE_AVISO[0] = ahora
                        _rl_logging.getLogger('django').error(
                            'rate_limit: el cache no respondió (%s) — contando en memoria del '
                            'proceso, el tope pasa a ser por worker.', nombre,
                        )
                    res = _rate_limit_en_memoria(key, tope, seconds)
                if res:
                    excedido = True
                    break

            if excedido:
                # `message` y `code` como el resto de la API del plugin: sin ellos el chat mostraba
                # «No se pudo conectar con el asistente», que es falso (auditoría del 2026-09-24).
                return JsonResponse({
                    "error": True, "code": "RATE_LIMIT",
                    "message": "Hay muchas consultas en este momento. Espera un minuto y vuelve a intentarlo.",
                }, status=429)
            return view_func(request, *args, **kwargs)
        return _wrapped
    return _apply
