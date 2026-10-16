import sys
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from core.custom_models import FormError
from core.funciones import addData, log, paginador, secure_module
from core.funciones_adicionales import salva_logs
from .forms import CierreCitaForm
from .funciones_citas import cancelar_cita, mover_cita, registrar_cierre, sincronizar_google
from .funciones_permisos import es_coordinador, es_lider_equipo
from .models import ESTADO_CITA, Cita, NotaCita


@login_required
@secure_module
def citaView(request, pk=None):
    data = {
        'titulo': 'Citas',
        'descripcion': 'Todas las citas en las que participas; los líderes ven las de su equipo.',
        'modulo': 'Agenda',
        'ruta': '/agenda/citas/',
        'fecha': str(date.today()),
    }
    addData(request, data)
    model = Cita
    cita = None
    if pk is not None:
        cita = (model.objects.filter(pk=pk, status=True).select_related('cliente', 'proyecto', 'equipo', 'producto', 'organizador')
                .first())
        if cita is None:
            raise Http404
        participa = cita.participantes.filter(status=True, usuario=request.user).exists()
        if not (participa or es_coordinador(request.user) or (cita.equipo_id and es_lider_equipo(request.user, cita.equipo))):
            messages.error(request, 'No participas en esta cita.')
            return JsonResponse({'error': True, 'message': 'Sin acceso.'}, status=403) if request.method == 'POST' else render(request, '403.html', data, status=403)
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            if cita is None:
                raise ValueError('Cita no indicada.')
            with transaction.atomic():
                if action == 'nota':
                    nota = NotaCita.objects.filter(cita=cita).first() or NotaCita(cita=cita)
                    nota.status = True
                    nota.texto = request.POST.get('texto', '')[:20000]
                    nota.save(request)
                    res_json.append({'error': False, 'guardado': datetime.now().strftime('%H:%M:%S')})
                elif action == 'cierre':
                    if cita.estado == 'cancelada':
                        raise ValueError('Una cita cancelada no se cierra.')
                    form = CierreCitaForm(request.POST, request=request, instance=getattr(cita, 'cierre', None))
                    if not form.is_valid():
                        raise FormError(form)
                    registrar_cierre(cita, form.cleaned_data, request.user, request)
                    log(f'Registró el cierre de la cita {cita.codigo}', request, 'add', obj=cita.id)
                    messages.success(request, 'Cierre guardado. La cita pasa a cerrada.')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'reprogramar':
                    inicio = datetime.strptime(request.POST['inicio'][:16], '%Y-%m-%dT%H:%M')
                    duracion = int(request.POST.get('duracion') or cita.duracion_min)
                    mover_cita(model.objects.select_for_update().get(pk=cita.pk), inicio, inicio + timedelta(minutes=duracion), request)
                    log(f'Reprogramó la cita {cita.codigo}', request, 'change', obj=cita.id)
                    messages.success(request, 'Cita reprogramada; se avisó a los invitados.')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'cancelar':
                    cancelar_cita(cita, request.POST.get('motivo', '').strip(), request)
                    log(f'Canceló la cita {cita.codigo}', request, 'change', obj=cita.id)
                    messages.success(request, 'Cita cancelada.')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'sincronizar':
                    if cita.estado == 'pendiente':
                        cita.estado = 'confirmada'
                        cita.save(request)
                        log(f'Confirmó de nuevo la cita {cita.codigo}', request, 'change', obj=cita.id)
                    transaction.on_commit(lambda: sincronizar_google(cita))
                    res_json.append({'error': False, 'reload': True})
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json = [{'error': True, 'message': str(ex)}]
        except FormError as ex:
            res_json = [ex.dict_error]
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json = [{'error': True, 'message': 'Intente nuevamente.'}]
        return JsonResponse(res_json, safe=False)
    elif request.method == 'GET':
        if cita is not None:
            data['titulo'] = cita.titulo
            data['descripcion'] = f'{cita.codigo} · {cita.cliente}'
            data['cita'] = cita
            data['participantes'] = cita.participantes.filter(status=True).select_related('usuario')
            data['nota'] = NotaCita.objects.filter(status=True, cita=cita).first()
            data['cierre'] = getattr(cita, 'cierre', None)
            data['form_cierre'] = CierreCitaForm(instance=data['cierre'])
            data['actividad'] = cita.actividad.select_related('autor').order_by('-creado_en')[:30]
            data['otras'] = (model.objects.filter(status=True, cliente=cita.cliente).exclude(pk=cita.pk)
                             .exclude(estado='cancelada').order_by('-inicio')[:5])
            data['puede_editar'] = cita.estado in ('confirmada', 'pendiente', 'realizada')
            return render(request, 'agenda/cita/detalle.html', data)
        criterio, estado = request.GET.get('criterio', '').strip(), request.GET.get('estado', '').strip()
        filtros, url_vars = Q(status=True), ''
        if not es_coordinador(request.user):
            filtros &= Q(participantes__usuario=request.user, participantes__status=True) | Q(equipo__lider=request.user) | Q(proyecto__lider=request.user)
        if criterio:
            filtros &= Q(codigo__icontains=criterio) | Q(titulo__icontains=criterio) | Q(cliente__nombres__icontains=criterio) | Q(cliente__correo__icontains=criterio)
            data['criterio'] = criterio
            url_vars += '&criterio=' + criterio
        if estado:
            filtros &= Q(estado=estado)
            data['estado'] = estado
            url_vars += '&estado=' + estado
        listado = model.objects.filter(filtros).select_related('cliente', 'proyecto', 'equipo').distinct().order_by('-inicio')
        data['estados'] = ESTADO_CITA
        data['list_count'] = listado.count()
        data['url_vars'] = url_vars
        paginador(request, listado, 20, data, url_vars)
        return render(request, 'agenda/cita/listado.html', data)
