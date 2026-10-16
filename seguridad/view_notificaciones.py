from datetime import date, datetime
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from core.funciones import addData, paginador, log
from django.db.models import Q
from seguridad.models import Notificacion, PRIORIDAD_NOTIFICACION, TIPO_NOTIFICACION


@login_required
def notificacionesView(request):
    data = {'titulo': 'Notificaciones',
            'modulo': 'Notificaciones',
            'ruta': request.path,
            'fecha': str(date.today())}
    persona = request.user
    addData(request, data)

    if request.method == 'POST':
        data["action"] = action = request.POST["action"]
        # 'check' es el nombre que manda el front (listado.html); 'ViewedNotification'
        # es el nombre legacy. Aceptamos los dos para no romper integraciones viejas.
        if action in ('check', 'ViewedNotification'):
            try:
                id = request.POST['id'] if 'id' in request.POST and request.POST['id'] else 0
                notificacion = Notificacion.objects.filter(pk=id, destinatario=persona).first()
                if not notificacion:
                    return JsonResponse({"error": True, "mensaje": u"Notificación no encontrada"})
                notificacion.leido = True
                notificacion.fecha_hora_leido = datetime.now()
                notificacion.save(request)
                log(u'Leo el mensaje: %s' % notificacion, request, "edit")
                # Devolvemos ambas keys (`error` para front nuevo, `result` para legacy).
                return JsonResponse({"error": False, "result": True, 'mensaje': u'Notificación marcada como leída'})
            except Exception as ex:
                return JsonResponse({"error": True, "result": False, "mensaje": u"Error: %s" % ex.__str__()})
        if action == 'checkall':
            # UPDATE masivo: «marcar todas» hacía un save() por notificación (podían ser cientos).
            actualizadas = Notificacion.objects.filter(destinatario_id=persona.id, leido=False, status=True).update(
                leido=True, fecha_hora_leido=datetime.now(),
            )
            log(f"Marcó todas las notificaciones como leidas {persona.datos()}", request, "change")
            messages.success(request, f"Se han marcado {actualizadas} notificaciones como leidas")
            res_json = {"error": False}
            return JsonResponse(res_json, safe=False)

    # Click en la campanita: marca la notificación como leída y redirige a su
    # URL de enlace directo (ej. la conversación). Si no tiene URL, vuelve al
    # origen o al panel.
    if request.GET.get('action') == 'abrirUrl':
        idn = request.GET.get('id') or 0
        notificacion = Notificacion.objects.filter(pk=idn, destinatario=persona).first()
        if notificacion:
            if not notificacion.leido:
                notificacion.leido = True
                notificacion.fecha_hora_leido = datetime.now()
                notificacion.save(request)
            destino = (notificacion.url or '').strip()
            if destino:
                return redirect(destino)
        return redirect(request.GET.get('urlOrigen') or '/panel/')

    filtros, url_vars = Q(destinatario=persona, status=True), ''
    prioridad, leido = request.GET.get('prioridad',''), request.GET.get('leido','')
    tipo = request.GET.get('tipo','')

    if prioridad:
        prioridad = int(prioridad)
        data['prioridad'] = prioridad
        url_vars += f'&prioridad={prioridad}'
        filtros = filtros & Q(prioridad=prioridad)

    if tipo:
        tipo = int(tipo)
        data['tipo'] = tipo
        url_vars += f'&tipo={tipo}'
        filtros = filtros & Q(tipo=tipo)

    if leido:
        data['leido'] = leido
        url_vars += f'&leido={leido}'
        if leido == '1':
            filtros = filtros & Q(leido=True)
        elif leido == '2':
            filtros = filtros & Q(leido=False)

    listado = Notificacion.objects.filter(filtros).order_by('leido', '-id')
    # count() en la base: len() traía TODAS las notificaciones a memoria solo para mostrar el total.
    data["totalCount"] = listado.count()
    data["url_vars"] = url_vars
    data["PRIORIDAD_NOTIFICACION"] = PRIORIDAD_NOTIFICACION
    data["TIPO_NOTIFICACION"] = TIPO_NOTIFICACION
    paginador(request, listado, 15, data)
    return render(request, 'seguridad/notificaciones/listado.html', data)
