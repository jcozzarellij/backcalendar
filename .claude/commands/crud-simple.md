---
description: Genera un CRUD simple (vista + form + url + templates) con el patrón `if action` de backcalendar.
argument-hint: <app> <recurso> [Modelo]
---

Generar un CRUD simple para backcalendar a partir de: `$ARGUMENTS`

Interpretar como `<app> <recurso> [Modelo]`. Si el modelo o sus campos no están claros, preguntar al usuario qué modelo y qué columnas/campos mostrar antes de generar nada. Leer las skills `django-backend`, `formmodal` y `design-guidelines-panel`, y replicar `area_geografica/view_pais.py` + `templates/area_geografica/pais/`. Todo el copy en español.

Si el modelo no existe, primero crearlo en `<app>/models.py` heredando `core.custom_models.ModeloBase` (choices a nivel de módulo) y avisar que hace falta `makemigrations`/`migrate` (aditivo).

### 1. NUEVO `<app>/view_<recurso>.py`

```python
import sys
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from core.custom_models import FormError
from core.funciones import addData, paginador, secure_module, log
from core.funciones_adicionales import salva_logs
from .forms import <Form>
from .models import <Modelo>


@login_required
@secure_module
def <recurso>View(request):
    data = {'titulo': '<Título plural>', 'modulo': '<Módulo>', 'ruta': request.path, 'fecha': str(date.today())}
    addData(request, data)
    model = <Modelo>
    Formulario = <Form>
    if request.method == 'POST':
        res_json = []
        action = request.POST['action']
        try:
            with transaction.atomic():
                if action == 'add':
                    form = Formulario(request.POST, request.FILES, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f"Registró <recurso> {form.instance}", request, "add", obj=form.instance.id)
                    messages.success(request, "Registro agregado")
                    res_json.append({'error': False, 'reload': True})
                elif action == 'change':
                    filtro = model.objects.get(pk=int(request.POST['pk']), status=True)
                    form = Formulario(request.POST, request.FILES, instance=filtro, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f"Editó <recurso> {filtro}", request, "change", obj=filtro.id)
                    messages.success(request, "Registro modificado")
                    res_json.append({'error': False, 'reload': True})
                elif action == 'delete':
                    filtro = model.objects.get(pk=int(request.POST['id']), status=True)
                    filtro.status = False
                    filtro.save(request)
                    log(f"Eliminó <recurso> {filtro}", request, "del", obj=filtro.id)
                    messages.success(request, "Registro eliminado")
                    res_json = {'error': False}
        except ValueError as ex:
            res_json.append({'error': True, 'message': str(ex)})
        except FormError as ex:
            res_json.append(ex.dict_error)
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       'Error on line {}'.format(sys.exc_info()[-1].tb_lineno), ex)
            res_json.append({'error': True, 'message': 'Intente nuevamente'})
        return JsonResponse(res_json, safe=False)
    elif request.method == 'GET':
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            try:
                if action == 'add':
                    data['form'] = Formulario()
                    template = get_template('<app>/<recurso>/form.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                elif action == 'change':
                    data['pk'] = pk = int(request.GET['pk'])
                    data['form'] = Formulario(instance=model.objects.get(pk=pk, status=True))
                    template = get_template('<app>/<recurso>/form.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
            except Exception as ex:
                return JsonResponse({'result': False, 'message': 'No se pudo cargar el formulario.'})
        criterio, filtros, url_vars = request.GET.get('criterio', '').strip(), Q(status=True), ''
        if criterio:
            filtros &= Q(<campo_busqueda>__icontains=criterio)
            data['criterio'] = criterio
            url_vars += '&criterio=' + criterio
        listado = model.objects.filter(filtros).order_by('<campo_orden>')
        data['list_count'] = listado.count()
        data['url_vars'] = url_vars
        paginador(request, listado, 20, data, url_vars)
        return render(request, '<app>/<recurso>/listado.html', data)
```

### 2. Form en `<app>/forms.py` (MODIFICAR, sin `git add`)

```python
class <Form>(ModelFormBase):
    class Meta:
        model = <Modelo>
        exclude = ('usuario_creacion', 'fecha_registro', 'usuario_modificacion', 'fecha_modificacion', 'status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['<campo>'].widget.attrs['col'] = '6'
```

`ModelFormBase` se importa de `core.custom_models`. Ya asigna `class` (select2, switchery, form-control) y `col=12`: solo ajustar `col` por campo; **no** pisar `class` en un loop. Unicidad con `clean_<campo>()` filtrando `status=True` y `.exclude(id=self.instance.id or 0)`.

### 3. URL en `<app>/urls.py` (MODIFICAR, sin `git add`)

Importar `from .view_<recurso> import <recurso>View` y agregar a la tupla `<app>_urls`:

```python
    {
        "nombre": "<Nombre legible>",
        "url": '<recurso>/',
        "vista": <recurso>View,
    },
```

Si la app es nueva, sumarla a `urls_sistema` en `backcalendar/urls.py`. Para que la pantalla aparezca en el sidebar y pase `@secure_module`, agregar la URL a `SECCIONES` en `scripts/seed_modulos.py` (o registrarla desde Mantenimiento de Url) y avisar al usuario.

### 4. NUEVO `templates/<app>/<recurso>/form.html`

Copiar `templates/autenticacion/usuario/formmodal.html` (campos en `col-lg-{{ field.field.widget.attrs.col }}`, hidden `action` y `pk` con `{{ pk|default:0 }}`, pie Cancelar `btn btn-danger btn-sm me-1` con `data-bs-dismiss="modal"` / Guardar `btn btn-success btn-sm`, `{{ form.media }}` y `{% include 'base_formulario_modal.html' %}`).

### 5. NUEVO `templates/<app>/<recurso>/listado.html`

Replicar `templates/area_geografica/pais/listado.html`: `{% extends 'base.html' %}`, filtros en `card mb-3` con `criterio`, botón «Nuevo …» `btn btn-success btn-sm` → `formModal(0, 'Nuevo …', 'add')`, tabla `#tabla.table.table-hover.table-striped` con columnas del modelo (nunca `status`), `{% empty %}` con mensaje útil, dropdown por fila con Editar (`formModal({{ l.pk }}, 'Editar …', 'change')`) y Eliminar (`eliminarajax({{ l.pk }}, '{{ l }}', 'delete')`, el global de `base.html`), `{% include "paginacion.html" %}`, shell `#modalDetalle` BS5 y en `{% block jscript %}` `forms.js` + la función `formModal` de la skill `formmodal`. Sin comentarios ni `<style>`; si hace falta CSS, `static/css/<app>/<recurso>.css?v1.0`.

### Al terminar

- `git add` solo de los archivos NUEVOS (`view_<recurso>.py`, `form.html`, `listado.html`, CSS si hubo); nunca de `forms.py` / `urls.py` / `models.py` modificados.
- No correr el servidor ni hacer commit. Verificar sintaxis con `pycheck`.
- Informar archivos creados/modificados y qué revisar en PyCharm (alta, edición, baja lógica, búsqueda, permisos del rol).
