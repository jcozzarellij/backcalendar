import sys
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from core.custom_models import FormError
from core.funciones import addData, log, paginador, secure_module
from core.funciones_adicionales import salva_logs
from .forms import PortalForm, ProductoForm
from .funciones_permisos import es_administrador
from .funciones_portal import qr_data_uri, tiempos_de
from .funciones_tokens import base_publica
from .models import Portal, Producto


@login_required
@secure_module
def portalView(request):
    data = {
        'titulo': 'Portales y productos',
        'descripcion': 'Lo que ve el cliente: cada portal con su marca y sus productos agendables.',
        'modulo': 'Agenda',
        'ruta': request.path,
        'fecha': str(date.today()),
    }
    addData(request, data)
    model = Portal
    Formulario = PortalForm
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if not es_administrador(request.user):
                    raise ValueError('Solo el líder general administra los portales.')
                if action == 'add':
                    form = Formulario(request.POST, request.FILES, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    if form.instance.principal:
                        model.objects.filter(status=True, principal=True).exclude(pk=form.instance.pk).update(principal=False)
                    log(f'Registró el portal {form.instance}', request, 'add', obj=form.instance.id)
                    messages.success(request, 'Portal registrado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'change':
                    filtro = model.objects.get(pk=int(request.POST['pk']), status=True)
                    form = Formulario(request.POST, request.FILES, instance=filtro, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    if filtro.principal:
                        model.objects.filter(status=True, principal=True).exclude(pk=filtro.pk).update(principal=False)
                    log(f'Editó el portal {filtro}', request, 'change', obj=filtro.id)
                    messages.success(request, 'Portal actualizado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'delete':
                    filtro = model.objects.get(pk=int(request.POST['id']), status=True)
                    if Producto.objects.filter(status=True, portal=filtro).exists():
                        raise ValueError('El portal tiene productos: elimínalos o muévelos primero.')
                    filtro.status = False
                    filtro.save(request)
                    log(f'Eliminó el portal {filtro}', request, 'del', obj=filtro.id)
                    messages.success(request, 'Portal eliminado')
                    res_json = {'error': False}
                elif action == 'addproducto':
                    portal = model.objects.get(pk=int(request.POST['pk']), status=True)
                    form = ProductoForm(request.POST, portal=portal, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.instance.portal = portal
                    form.save()
                    log(f'Registró el producto {form.instance} en {portal}', request, 'add', obj=form.instance.id)
                    messages.success(request, 'Producto registrado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'changeproducto':
                    producto = Producto.objects.select_related('portal').get(pk=int(request.POST['pk']), status=True)
                    form = ProductoForm(request.POST, instance=producto, portal=producto.portal, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f'Editó el producto {producto}', request, 'change', obj=producto.id)
                    messages.success(request, 'Producto actualizado')
                    res_json.append({'error': False, 'reload': True})
                elif action == 'delproducto':
                    producto = Producto.objects.get(pk=int(request.POST['id']), status=True)
                    if Producto.objects.filter(status=True, padre=producto).exists():
                        raise ValueError('Tiene subproductos: elimínalos primero.')
                    producto.status = False
                    producto.save(request)
                    log(f'Eliminó el producto {producto}', request, 'del', obj=producto.id)
                    messages.success(request, 'Producto eliminado')
                    res_json = {'error': False}
                elif action == 'activarproducto':
                    producto = Producto.objects.get(pk=int(request.POST['id']), status=True)
                    producto.activo = not producto.activo
                    producto.save(request)
                    log(f'{"Activó" if producto.activo else "Pausó"} el producto {producto}', request, 'change', obj=producto.id)
                    messages.success(request, 'Producto activado' if producto.activo else 'Producto en pausa')
                    res_json = {'error': False}
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
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            try:
                if action == 'add':
                    data['form'] = Formulario()
                    template = get_template('agenda/parciales/form_campos.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                elif action == 'change':
                    data['pk'] = pk = int(request.GET['pk'])
                    data['form'] = Formulario(instance=model.objects.get(pk=pk, status=True))
                    template = get_template('agenda/parciales/form_campos.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                elif action == 'addproducto':
                    data['pk'] = pk = int(request.GET['pk'])
                    portal = model.objects.get(pk=pk, status=True)
                    data['form'] = ProductoForm(portal=portal, initial={'padre': request.GET.get('padre') or None})
                    template = get_template('agenda/parciales/form_campos.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                elif action == 'changeproducto':
                    data['pk'] = pk = int(request.GET['pk'])
                    producto = Producto.objects.select_related('portal').get(pk=pk, status=True)
                    data['form'] = ProductoForm(instance=producto, portal=producto.portal)
                    template = get_template('agenda/parciales/form_campos.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                elif action == 'incrustar':
                    portal = model.objects.get(pk=int(request.GET['pk']), status=True)
                    data.update({'portal': portal, 'url': f'{base_publica()}/incrustar/{portal.slug}/', 'sitios': portal.sitios_autorizados.strip()})
                    template = get_template('agenda/portal/incrustar.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                elif action == 'enlace':
                    producto = Producto.objects.select_related('portal').get(pk=int(request.GET['pk']), status=True)
                    url = f'{base_publica()}/agendar/{producto.slug}/'
                    data.update({'producto': producto, 'url': url, 'qr': qr_data_uri(url)})
                    template = get_template('agenda/portal/enlace.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
            except Exception as ex:
                salva_logs(request, __file__, request.method, action, type(ex).__name__,
                           'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
                return JsonResponse({'result': False, 'message': 'No se pudo cargar el formulario.'})
        criterio, filtros, url_vars = request.GET.get('criterio', '').strip(), Q(status=True), ''
        if criterio:
            filtros &= Q(nombre__icontains=criterio) | Q(slug__icontains=criterio)
            data['criterio'] = criterio
            url_vars += '&criterio=' + criterio
        subproductos = Producto.objects.filter(status=True).select_related('equipo').order_by('orden', 'nombre')
        raices = (Producto.objects.filter(status=True, padre__isnull=True).select_related('equipo')
                  .prefetch_related(Prefetch('subproductos', queryset=subproductos, to_attr='hijos')).order_by('orden', 'nombre'))
        listado = list(model.objects.filter(filtros).prefetch_related(Prefetch('productos', queryset=raices, to_attr='raices')).order_by('-principal', 'nombre'))
        elegido = request.GET.get('portal', '')
        portal_actual = next((p for p in listado if str(p.pk) == elegido), listado[0] if listado else None)
        producto_actual = None
        if portal_actual is not None:
            pk_prod = request.GET.get('producto', '')
            candidatos = []
            for raiz in portal_actual.raices:
                candidatos.append(raiz)
                candidatos.extend(raiz.hijos)
            producto_actual = next((p for p in candidatos if str(p.pk) == pk_prod), candidatos[0] if candidatos else None)
        compartir = None
        if producto_actual is not None:
            url = f'{base_publica()}/agendar/{producto_actual.slug}/'
            compartir = {
                'producto': producto_actual, 'url': url, 'url_ventana': url + '?ventana=1', 'qr': qr_data_uri(url),
                'iframe': f'<iframe src="{url}?ventana=1" title="Agendar una cita" style="width:100%;min-height:720px;border:0;border-radius:16px" loading="lazy"></iframe>',
                'tiempos': tiempos_de(producto_actual),
            }
        data.update({
            'puede_editar': es_administrador(request.user), 'base_publica': base_publica(), 'portales': listado,
            'portal_actual': portal_actual, 'producto_actual': producto_actual, 'compartir': compartir,
            'list_count': len(listado), 'url_vars': url_vars,
        })
        return render(request, 'agenda/portal/listado.html', data)
