from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from core.funciones import addData, get_decrypt, get_client_ip, log, rate_limit
from django.contrib.auth import authenticate, login, logout
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
from django.utils.timezone import activate
from autenticacion import funciones_login_google
from backcalendar import settings

activate(settings.TIME_ZONE)

CLAVE_ERROR_GOOGLE = 'login_google_error'


def _destino_seguro(request, destino):
    """Devuelve `destino` solo si es una URL local (mismo host, sin esquema externo); si no,
    None. Cierra el open-redirect: `?next=https://sitio-malicioso` deja de reenviar afuera."""
    if destino and url_has_allowed_host_and_scheme(
            destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return destino
    return None


@rate_limit(limit=15, seconds=60)
def login_tienda(request):
    data = {'titulo': 'Iniciar Sesión', 'url_auth':True}
    addData(request, data)
    if request.method == 'GET':
        des, data['next'] = get_decrypt(request.GET.get('next'))
        if not des:
            data['next'] = request.GET.get('next')
        if request.user.username != "":
            return redirect('/panel/')
        data['login_google'] = funciones_login_google.habilitado()
        data['error_google'] = request.session.pop(CLAVE_ERROR_GOOGLE, '')
        return render(request, 'public/seguridad/sigin.html', data)
    datos = {'resp': False}
    try:
        addData(request, data)
        if request.method == 'POST':
            usuario_, password = request.POST['usuario'], request.POST['password']
            user = authenticate(username=usuario_, password=password)
            if user is not None and user.is_active:
                login(request, user)
                datos['resp'] = True
                ipreal = get_client_ip(request)
                ip = ipreal if ipreal != '127.0.0.1' else '127.0.0.1'
                log(f"Ha iniciado sesion desde la ip: {ip}", request, "add", obj='login')
                destino = _destino_seguro(request, request.POST.get('next'))
                if destino:
                    datos['redirect'] = destino
            else:
                # Mensaje genérico a propósito: no revelar si el usuario existe (evita enumeración).
                datos['error'] = 'Usuario o contraseña incorrectos'
            return JsonResponse(datos)
    except Exception as ex:
        datos['error'] = 'Credenciales Incorrectas'
        messages.error(request, ex)
        return JsonResponse(datos)


@rate_limit(limit=15, seconds=60)
def login_google(request):
    if not funciones_login_google.habilitado():
        raise Http404
    if request.user.is_authenticated:
        return redirect('/panel/')
    des, siguiente = get_decrypt(request.GET.get('next'))
    if not des:
        siguiente = request.GET.get('next')
    try:
        return redirect(funciones_login_google.url_inicio(request, _destino_seguro(request, siguiente)))
    except funciones_login_google.ErrorLoginGoogle as ex:
        request.session[CLAVE_ERROR_GOOGLE] = str(ex)
        return redirect('/login/')


@rate_limit(limit=15, seconds=60)
def login_google_callback(request):
    if not funciones_login_google.habilitado():
        raise Http404
    try:
        usuario = funciones_login_google.resolver_usuario(request)
    except funciones_login_google.ErrorLoginGoogle as ex:
        request.session[CLAVE_ERROR_GOOGLE] = str(ex)
        return redirect('/login/')
    siguiente = _destino_seguro(request, funciones_login_google.siguiente_guardado(request))
    login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')
    log(f"Ha iniciado sesion con Google desde la ip: {get_client_ip(request)}", request, "add", obj='login')
    return redirect(siguiente or '/panel/')


def logout_tienda(request):
    logout(request)
    return redirect('/')
