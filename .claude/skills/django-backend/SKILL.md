---
name: django-backend
description: Usar al escribir o modificar modelos, vistas por función con dispatch `if action` (add/change/delete), formularios (ModelFormBase/FormBase/FormModeloBase), consultas ORM, transacciones, soft delete, permisos (@secure_module / @solo_administrador) o cualquier lógica backend de backcalendar.
---

# Django backend (backcalendar)

Cómo se implementa el backend. Las reglas duras (ModeloBase, soft delete, choices a nivel de módulo, estructura `if action`, migraciones, git) están en `CODING_STANDARDS.md` (modelos, views, soft delete, uploads) y `CLAUDE.md` (migraciones, git) y mandan sobre esta skill; acá va el *cómo*, con el código real del repo.

Referencias canónicas: `area_geografica/view_pais.py` (CRUD mínimo), `seguridad/view_modulos_sistema.py` (acciones extra inline), `autenticacion/adm_usuario.py` (vista grande con `@solo_administrador`).

## Vista canónica

Una función por recurso, `data` + `addData`, POST con un único `try` + `with transaction.atomic()`, GET con acciones de fragmento y luego el listado.

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
from .forms import PaisForm
from .models import Pais


@login_required
@secure_module
def paisView(request):
    data = {'titulo': 'Países', 'modulo': 'Área Geográfica', 'ruta': request.path, 'fecha': str(date.today())}
    addData(request, data)
    model = Pais
    Formulario = PaisForm
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
                    log(f"Registró un país {form.instance}", request, "add", obj=form.instance.id)
                    res_json.append({'error': False, 'reload': True})
                elif action == 'change':
                    filtro = model.objects.get(pk=int(request.POST['pk']), status=True)
                    form = Formulario(request.POST, request.FILES, instance=filtro, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.save()
                    log(f"Editó un país {filtro}", request, "change", obj=filtro.id)
                    res_json.append({'error': False, 'reload': True})
                elif action == 'delete':
                    filtro = model.objects.get(pk=int(request.POST['id']), status=True)
                    filtro.status = False
                    filtro.save(request)
                    log(f"Eliminó un país {filtro}", request, "del", obj=filtro.id)
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
            if action == 'add':
                data['form'] = Formulario()
                template = get_template('area_geografica/pais/form.html')
                return JsonResponse({'result': True, 'data': template.render(data)})
            elif action == 'change':
                data['pk'] = pk = int(request.GET['pk'])
                data['form'] = Formulario(instance=model.objects.get(pk=pk, status=True))
                template = get_template('area_geografica/pais/form.html')
                return JsonResponse({'result': True, 'data': template.render(data)})
        criterio, filtros, url_vars = request.GET.get('criterio', '').strip(), Q(status=True), ''
        if criterio:
            filtros &= Q(nombre__icontains=criterio)
            data['criterio'] = criterio
            url_vars += '&criterio=' + criterio
        listado = model.objects.filter(filtros)
        data['list_count'] = listado.count()
        data['url_vars'] = url_vars
        paginador(request, listado, 20, data, url_vars)
        return render(request, 'area_geografica/pais/listado.html', data)
```

Puntos que no son obvios:
- **`ATOMIC_REQUESTS` está en `False`** (`backcalendar/settings.py`). El `with transaction.atomic()` del POST es la única transacción: toda escritura de varios pasos va dentro. Para concurrencia, `select_for_update()` dentro de ese bloque.
- El código de cada acción va **inline** en su rama. Lógica de dominio reutilizable → `<app>/funciones_<tema>.py` (ej. `autenticacion/funciones_autenticacion.py`, `seguridad/funciones_cron.py`), nunca `def` sueltos en el `view_*.py`.
- `log(mensaje, request, accion, obj=pk)`: `accion` es `"add"`, `"del"` (borrado) o cualquier otro valor → CHANGE. `"delete"` se registra como cambio: usar `"del"`.
- El `except Exception` genérico registra con `salva_logs(...)` (tabla `ErrorLog`) y responde un mensaje neutro; no exponer `str(ex)` al usuario.
- El GET de `change` recibe `pk` (lo manda `formModal` y `ajaxVerModal` de `base.html`); el `delete` recibe `id` (lo manda `eliminarajax`).
- Cuando la respuesta solo recarga, el texto va por `messages.success(...)`: `base.html` lo pinta como toast al recargar.

### Contratos JSON

| Contexto | Forma |
|---|---|
| POST add/change OK | `[{'error': False, 'reload': True}]` o `'to': '/url/'` |
| POST delete OK | `{'error': False}` (dict: lo lee `eliminarajax`) |
| POST error de formulario | `ex.dict_error` de `FormError(form)` → `{'error': True, 'form': [{campo: msg}], 'message': ...}` |
| POST otro error | `{'error': True, 'message': '...'}` |
| GET fragmento | `{'result': True, 'data': html}` (+ `'titulo'` si lo abre `verModalPostAjax`) |
| GET fallo | `{'result': False, 'message': '...'}` |

## Modelos

```python
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q

from core.custom_models import ModeloBase
from core.validadores import validate_file_size_2mb

ESTADO_RESERVA = (
    (1, 'PENDIENTE'),
    (2, 'CONFIRMADA'),
)


class Reserva(ModeloBase):
    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    estado = models.IntegerField(choices=ESTADO_RESERVA, default=1, verbose_name='Estado')
    ciudad = models.ForeignKey('area_geografica.Ciudad', on_delete=models.PROTECT, verbose_name='Ciudad')
    adjunto = models.FileField(upload_to='reservas/', blank=True, null=True, verbose_name='Adjunto',
                               validators=[FileExtensionValidator(['pdf']), validate_file_size_2mb])

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ('-fecha_registro',)
        constraints = [
            models.UniqueConstraint(fields=['nombre'], name='reserva_nombre_unico', condition=Q(status=True)),
        ]
```

- `ModeloBase` (`core/custom_models.py`) ya da `usuario_creacion`, `fecha_registro`, `usuario_modificacion`, `fecha_modificacion`, `status`. No declarar `fecha`, `creado_en`, `creado_por`, etc. `activo` sí puede convivir con `status`.
- `save()` toma el usuario de `request=` o, si no viene, del middleware (`core.custom_middleware.get_current_request`). La convención es `obj.save(request)`. Respeta `update_fields` (le suma los campos de auditoría).
- Evidencia que no se edita ni borra → `core.custom_models.RegistroInmutable` (su `save()` rechaza updates y `delete()` lanza). Ledgers/logs append-only existentes (`ErrorLog`, `AudiUsuarioTabla`, `CronLogEjecucion`, `SessionUser`) son las únicas excepciones; no agregar nuevas sin pedirlo.
- Choices **siempre a nivel de módulo** (`REGION_CHOICES` en `area_geografica/models.py`, `PRIORIDAD_NOTIFICACION` en `seguridad/models.py`). `Usuario.TIPO_DOCUMENTO`/`SEXO` dentro de la clase es legado: no imitar.
- Unicidad entre activos: `UniqueConstraint(..., condition=Q(status=True))` (ver `Pais`).
- `get_or_create`/`update_or_create` sobre clave única: `status` va en `defaults`, no en la búsqueda.
- Archivos: `FileExtensionValidator` + validador de tamaño de `core/validadores.py` (`validate_file_size_2mb`, `_3mb`, `_20mb`, o `FileMaxSizeInMbValidator(n)`). Nombres de archivo: `core.models_utils.FileNameUploadToPath`.

## Formularios

| Clase | Dónde | Uso |
|---|---|---|
| `ModelFormBase` | `core/custom_models.py` | ligado a modelo (lo normal) |
| `FormBase` | `core/custom_models.py` | sin modelo, mismas comodidades |
| `FormModeloBase` | `core/custom_forms.py` | sin modelo, versión simple |
| `ExtFileField(ext_whitelist=..., max_upload_size=...)` | `core/custom_forms.py` | archivo en form sin modelo |

`ModelFormBase` ya pone las clases solo: `select2` en FK/M2M, `form-control` en el resto, `js-switch` (switchery) en booleanos, `type=date`/`time`, asterisco rojo en requeridos, `col=12` por defecto, `accept` según el `FileExtensionValidator` del modelo y `readonly` con `ver=True`. **No** sobrescribir `class` en un loop: rompe select2 y switchery. Solo ajustar `col` y lo puntual.

Kwargs útiles al instanciar: `request=request` (lo usa `save()` para auditoría), `ver=True`, `no_requeridos=[...]`, `requeridos=[...]`, `querysets={'campo': qs}`, `no_select2=[...]`, `no_switchery=[...]`.

```python
from django.core.exceptions import ValidationError

from area_geografica.models import Ciudad
from core.custom_models import ModelFormBase
from .models import Reserva


class ReservaForm(ModelFormBase):
    class Meta:
        model = Reserva
        exclude = ('usuario_creacion', 'fecha_registro', 'usuario_modificacion', 'fecha_modificacion', 'status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].widget.attrs['col'] = '6'
        self.fields['ciudad'].queryset = Ciudad.objects.filter(status=True)

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        if Reserva.objects.filter(status=True, nombre__iexact=nombre).exclude(id=self.instance.id or 0).exists():
            raise ValidationError('Ya existe una reserva con este nombre')
        return nombre
```

`FormError` existe en `core/custom_models.py` y en `core/custom_forms.py`; las vistas importan el de `core.custom_models`.

## ORM

- `select_related` para FK, `prefetch_related` para inversas/M2M; filtrar `status=True` también en relaciones (`Count('provincia', filter=Q(provincia__status=True))`).
- KPIs en un solo `aggregate(total=Count('id'), x=Count('id', filter=Q(...)))`, nunca contando en Python.
- `F()` para incrementos atómicos. Para JSON no hacer `json.dumps(list(qs.values()))` con `Decimal`/`datetime`: convertir campo a campo.
- `USE_TZ = False`, `TIME_ZONE = 'America/Guayaquil'`: fechas naive locales.

## Permisos y helpers (`core/funciones.py`)

| Helper | Para qué |
|---|---|
| `@login_required` + `@secure_module` | siempre, en ese orden. Superusuario pasa; `is_staff` pasa si la URL está en un `Modulo` de algún `GroupModulo` de sus grupos |
| `@solo_administrador` | pantallas globales: superusuario o grupo `ID_GRUPO_ADMINISTRADOR` |
| `addData(request, data)` | contexto común: `confi`, `nombreempresa`, `dict_url_vars`, sidebar, notificaciones |
| `paginador(request, qs, n, data, url_vars)` | pagina en `data['listado']` |
| `log(...)` / `salva_auditoria(request, model, action, nombre, qs_nuevo, qs_anterior)` | bitácora / auditoría con antes-después |
| `notificacion(titulo, cuerpo, destinatario, url, prioridad, tipo=1, request=None)` | notificación interna |
| `@rate_limit(limit, seconds)` | endpoints públicos o de consulta (ej. `core/ajax.py`) |
| `core.correos.despachar(core.correos.armar(asunto, html, to=[...]))` | correo fuera del request; `core.email_config.send_html_mail` es la puerta legada |

Consultas AJAX transversales sin pantalla propia: rama en `core/ajax.py::ConsultasAjax` (`/ajaxrequest/<accion>`).

## Trampas

- Olvidar `status=True` en una lectura, o filtrarlo en la búsqueda de un `get_or_create` con clave única.
- `.delete()` físico: siempre `status=False` + `save(request)`.
- Escrituras de varios pasos fuera de `transaction.atomic()` (no hay `ATOMIC_REQUESTS`).
- Pasar `str(ex)` al usuario en el `except Exception`.
- Copy en inglés: mensajes, `messages.*`, excepciones y `JsonResponse` van en español.
