import string
from random import choice

from django.contrib.auth import authenticate
from django.contrib.auth.models import Group

from backcalendar.settings import ID_GRUPO_ADMINISTRADOR


def habilitar_acceso_administrativo(usuario, request=None):
    """Da acceso al panel: `is_staff` y el grupo Administrador de settings. Devuelve el usuario."""
    if not usuario.is_staff or not usuario.status or not usuario.is_active:
        usuario.is_staff = True
        usuario.is_active = True
        usuario.status = True
        usuario.save(request) if request is not None else usuario.save()
    usuario.groups.add(Group.objects.get(pk=ID_GRUPO_ADMINISTRADOR))
    return usuario


def cambiar_password_propia(usuario, clave_actual, clave_nueva):
    """Cambio de clave por el propio usuario: exige la clave actual y rechaza
    que la nueva sea igual a la actual. Devuelve (ok, mensaje)."""
    if authenticate(username=usuario.username, password=clave_actual) is None:
        return False, 'Contraseña actual incorrecta'
    if clave_actual == clave_nueva:
        return False, 'La contraseña nueva debe ser diferente a la contraseña actual'
    usuario.set_password(clave_nueva)
    usuario.save()
    return True, 'Contraseña actualizada con éxito'


def cambiar_password_forzada(usuario, clave_nueva):
    """Cambio de clave sin verificar la actual -- para el flujo de `cambio_clave`
    obligatorio (ya se validó la sesión). No hace login(), eso lo decide la vista."""
    usuario.set_password(clave_nueva)
    usuario.cambio_clave = False
    usuario.save()
    return True, 'Contraseña actualizada con éxito'


def cambiar_password_admin(usuario_objetivo, clave_nueva, request):
    """Un administrador resetea la clave de otro usuario -- acción administrativa,
    sin verificar la clave actual del usuario objetivo."""
    usuario_objetivo.set_password(clave_nueva)
    usuario_objetivo.save(request)
    return True, 'Contraseña de {} / {} cambiada'.format(
        usuario_objetivo.get_full_name(), usuario_objetivo.username,
    )


def cambiar_username(usuario, nuevo_username):
    """Valida unicidad y cambia el username. Devuelve (ok, mensaje)."""
    from .models import Usuario

    if Usuario.objects.filter(username=nuevo_username).exclude(pk=usuario.pk).exists():
        return False, 'Ya existe un usuario con ese nombre de usuario.'
    usuario.username = nuevo_username
    usuario.save()
    return True, 'Modificado correctamente.'


def proteger_objetivo_superuser(request, user):
    """Un administrador que NO es superusuario no puede gestionar (resetear la clave, activar,
    desactivar, reperfilar o renombrar) a un SUPERUSUARIO: sin esto, un admin común podía
    apoderarse de la cuenta de plataforma reseteándole la contraseña, o degradar a otro admin
    superior. Corta con un ValueError que las vistas de usuarios devuelven como mensaje."""
    if getattr(user, 'is_superuser', False) and not request.user.is_superuser:
        raise ValueError('No tienes permiso para gestionar una cuenta de superusuario.')


def generar_clave_temporal(largo=10):
    alfabeto = string.ascii_letters + string.digits
    return ''.join(choice(alfabeto) for _ in range(largo))


def _reset_permitido_para(email, limite=3, ventana_seg=3600):
    """Throttle POR CORREO del restablecimiento: aunque el atacante rote IPs (el rate-limit por
    vista keyea por IP), no puede resetear la MISMA cuenta más de `limite` veces por hora — así
    no se puede dejar a una persona sin acceso a fuerza de restauraciones. Cuasi-atómico."""
    import hashlib

    from django.core.cache import cache

    clave = 'reset_email:' + hashlib.sha256((email or '').strip().lower().encode()).hexdigest()[:20]
    if cache.add(clave, 1, timeout=ventana_seg):
        return True
    try:
        return cache.incr(clave) <= limite
    except ValueError:
        cache.set(clave, 1, timeout=ventana_seg)
        return True


def solicitar_restauracion_clave(email):
    """Busca un Usuario activo por email, excluye administradores activos (self-service
    de restaurar clave no aplica a Administrador -- debe pedirle a otro admin), genera
    una clave temporal, la aplica y envía el correo. Devuelve (ok, mensaje).

    Nota: reemplaza el filtro previo por perfil administrativo de
    public/view_restaurar.py, que exigía tener un perfil administrativo
    (activa o no) para siquiera encontrar al usuario -- eso bloqueaba por accidente a
    los clientes puros (sin perfil administrativo jamás creado), justo a quienes esta
    función está destinada a servir. La regla real es la de la línea de abajo:
    activo y sin perfil administrativo activo.
    """
    import time

    from core.email_config import send_html_mail
    from seguridad.models import Configuracion
    from backcalendar import settings
    from .models import Usuario

    usuario = Usuario.objects.filter(email=email, status=True).first()
    if not usuario:
        return False, 'No existe usuario asociado a este correo.'
    if not usuario.is_active:
        return False, 'Usuario deshabilitado.'
    if usuario.es_administrativo():
        return False, 'Los administradores deben solicitar el cambio de contraseña a otro administrador.'
    if not _reset_permitido_para(email):
        # Ya se restauró esta cuenta varias veces en la última hora: no se vuelve a cambiar la
        # clave (protege del lockout dirigido). La vista responde neutro igual.
        return False, 'Demasiadas solicitudes de restauración para este correo. Intentá más tarde.'

    codigo = generar_clave_temporal()
    usuario.set_password(codigo)
    usuario.save()

    confi = Configuracion.objects.first()
    datos = {
        'sucursal': confi.nombre_empresa if confi else '',
        'usuario': str(usuario.username),
        'codigo': str(codigo),
        'fecha': str(time.strftime("%Y-%m-%d %H:%M")),
        'correo': str(settings.EMAIL_HOST_USER),
    }
    send_html_mail('Cambio de contraseña', 'email/recuperar.html', datos, [email], [], [])
    return True, 'Clave restaurada, revise su dirección de correo electrónico.'
