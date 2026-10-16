# Estudio — Cómo programamos las vistas por función y cómo reutilizar el CSS

Fecha: 2026-10-08 · Estado: estudio (sin cambios de código)

Medido sobre el código actual de backcalendar: 23 vistas por función, 18 archivos CSS propios y 67 plantillas. Sirve de base para la app nueva `agenda` (ver `docs/plan_micrositio_agendas.md`).

---

## Parte 1 — Vistas basadas en funciones

### 1.1 El patrón que usamos

Todas las pantallas son **una función por recurso** que despacha por `action`. La referencia es `area_geografica/view_pais.py`; la más completa, `autenticacion/adm_usuario.py`.

```
@login_required
@secure_module                      (+ @solo_administrador en pantallas globales)
def recursoView(request):
    data = {'titulo', 'descripcion', 'modulo', 'ruta', 'fecha'}
    addData(request, data)
    model, Formulario = Modelo, ModeloForm
    if request.method == 'POST':
        res_json = []
        action = request.POST['action']
        try:
            with transaction.atomic():
                if action == 'add':      form → save → log(..., "add") → {'error': False, 'to'/'reload'}
                elif action == 'change': get(pk) → form(instance) → save → log(..., "change")
                elif action == 'delete': get(pk) → status=False → save(request) → log(..., "del")
        except ValueError  → {'error': True, 'message': str(ex)}
        except FormError   → ex.dict_error
        except Exception   → salva_logs(...) + mensaje neutro
        return JsonResponse(res_json, safe=False)
    elif request.method == 'GET':
        if 'action' in request.GET:  add / change → render del form.html en JSON {'result', 'data'}
        filtros Q(status=True) + criterio + url_vars → paginador → render listado.html
```

Piezas de `core` que lo sostienen: `addData`, `secure_module`, `solo_administrador`, `paginador`, `log`, `salva_logs`, `redirectAfterPostGet`, `FormError`, `ModelFormBase`. Del lado del navegador, el formulario en modal (`formModal` + `forms.js`) y `eliminarajax`.

### 1.2 Cómo están hoy (inventario)

| Vista | Líneas | Cumple el patrón | Desvíos encontrados |
|---|---|---|---|
| `area_geografica/view_pais.py` · `view_provincia.py` · `view_ciudad.py` | ~100 c/u | Sí | `addData` solo en GET; acciones GET sin `try`; `get(pk)` sin `status=True`; las tres son casi idénticas |
| `autenticacion/adm_usuario.py` | 294 | Sí | Larga; devuelve `str(ex)` en algunos errores |
| `autenticacion/view_perfil.py` | 262 | Parcial | `.delete()` físico sobre suscripciones push y sesiones (no son `ModeloBase`: aceptable) |
| `seguridad/view_grupo.py` | 197 | Sí | `group.delete()` físico (es `auth.Group`, no `ModeloBase`) |
| `seguridad/view_modulogrupo.py` | 203 | Sí | — |
| `seguridad/view_modulos_sistema.py` | 274 | Sí | Responde con `HttpResponse(json.dumps(...))` en `act_orden`, distinto del resto |
| `seguridad/view_modulo.py` · `view_grupourls.py` · `view_arbol_modulogrupo.py` | 80–110 | Sí | — |
| `seguridad/view_configuracion.py` · `view_configuracion_terminos.py` | 50–110 | Sin `action` (un solo formulario) | Correcto para una fila única |
| `seguridad/adm_crons.py` · `view_databasebackup.py` | 57–73 | Sí | **Helpers sueltos** en la vista (`_tolerancia_seg`, `_estado`, `_archivo_seguro`): van a `funciones_*.py` |
| `seguridad/view_webpush_broadcast.py` | 237 | Parcial | `.delete()` físico de suscripciones (webpush) |
| `seguridad/view_notificaciones.py` | 84 | Parcial | **Sin `@secure_module`** (la ve todo usuario: confirmar que es intencional) |
| `seguridad/view_auditoria.py`, `view_index_adm.py` | 15–35 | Solo listado | — |
| `public/view_login.py` | 33 | Pública | Helper suelto `_destino_seguro` |
| `pwa/views.py` | 2–24 | Endpoints técnicos | Helpers sueltos `_get_configuracion`, `_build_icons` |

### 1.3 Lo que hay que corregir en el patrón antes de copiarlo a `agenda`

1. **`addData` al inicio**, antes del `if request.method`. En país, provincia y ciudad está solo en GET, y las acciones POST no tienen el contexto de usuario.
2. **Acciones GET dentro de `try`**, con `{'result': False, 'message': ...}`. Hoy un `pk` inexistente da error 500.
3. **Leer con `status=True`**: `model.objects.get(pk=pk, status=True)`. Hoy se puede editar o «borrar» un registro ya dado de baja.
4. **Una sola forma de respuesta en POST**: siempre la lista `res_json`. En `delete`, la variable se reasigna a un dict.
5. **Nunca `str(ex)` en el `except Exception` genérico**: `salva_logs` + «Intente nuevamente». `str(ex)` solo en `ValueError`, que lleva mensajes escritos por nosotros.
6. **`select_related`/`prefetch_related`** en los listados que muestran FK.
7. **El nombre de la acción de borrado en `log`** es `"del"` (`core/funciones.log` reconoce `"del"`; con `"delete"` el borrado queda registrado como cambio).
8. **Helpers fuera de la vista**: todo `_funcion` de un `view_*.py` va a `<app>/funciones_*.py` (regla de `CLAUDE.md`).

Esqueleto corregido para las vistas nuevas de `agenda`:

```python
@login_required
@secure_module
def turnosView(request):
    data = {'titulo': 'Mis turnos', 'descripcion': 'Tu semana tipo y sus excepciones.',
            'modulo': 'Agenda', 'ruta': request.path, 'fecha': str(date.today())}
    addData(request, data)
    model, Formulario = ExcepcionTurno, ExcepcionTurnoForm
    if request.method == 'POST':
        res_json = []
        action = request.POST.get('action', '')
        try:
            with transaction.atomic():
                if action == 'add':
                    form = Formulario(request.POST, request=request)
                    if not form.is_valid():
                        raise FormError(form)
                    form.instance.usuario = request.user
                    form.save()
                    log(f'Registró excepción {form.instance}', request, 'add', obj=form.instance.id)
                    res_json.append({'error': False, 'reload': True})
                elif action == 'delete':
                    filtro = model.objects.get(pk=int(request.POST['id']), usuario=request.user, status=True)
                    filtro.status = False
                    filtro.save(request)
                    log(f'Eliminó excepción {filtro}', request, 'del', obj=filtro.id)
                    res_json.append({'error': False})
                else:
                    raise ValueError('Acción no permitida.')
        except ValueError as ex:
            res_json.append({'error': True, 'message': str(ex)})
        except FormError as ex:
            res_json.append(ex.dict_error)
        except Exception as ex:
            salva_logs(request, __file__, request.method, action, type(ex).__name__,
                       f'Error on line {sys.exc_info()[-1].tb_lineno}', ex)
            res_json.append({'error': True, 'message': 'Intente nuevamente.'})
        return JsonResponse(res_json, safe=False)
    elif request.method == 'GET':
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            try:
                if action == 'add':
                    data['form'] = Formulario()
                    template = get_template('agenda/turnos/form.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                elif action == 'disponibilidad':
                    return JsonResponse({'result': True, **calcular_semana(request.user, request.GET)})
                return JsonResponse({'result': False, 'message': 'Acción no permitida.'})
            except Exception as ex:
                salva_logs(request, __file__, request.method, action, type(ex).__name__,
                           f'Error on line {sys.exc_info()[-1].tb_lineno}', ex)
                return JsonResponse({'result': False, 'message': 'No se pudo cargar.'})
        listado = model.objects.filter(status=True, usuario=request.user).order_by('desde')
        paginador(request, listado, 20, data, '')
        return render(request, 'agenda/turnos/listado.html', data)
```

### 1.4 Reutilizar sin romper la regla «código inline en cada acción»

La regla del repo pide el CRUD inline en cada rama. Lo reutilizable va así:

| Qué se repite | Dónde va | Ejemplo en `agenda` |
|---|---|---|
| Lógica de dominio (calcular, asignar, hablar con Google) | `agenda/funciones_*.py` | `calcular_disponibilidad(...)`, `crear_evento_google(...)` |
| Consultas que usan varias pantallas | Métodos del modelo o del manager | `Cita.objects.del_dia(usuario, fecha)` |
| Permisos por rol más allá del módulo | Una función de `agenda/funciones_permisos.py` llamada al inicio de cada acción | `puede_reprogramar(usuario, cita)` |
| Respuestas JSON para el calendario o los tableros | Acciones GET de la misma vista | `?action=eventos&desde=&hasta=` |
| Plantillas repetidas | `{% include %}` de parciales en `templates/agenda/parciales/` | tarjeta de reunión, chip de estado, fila de cola |

Lo que **no** se hace: vistas genéricas de Django ni un «CRUD base» que esconda las ramas. País, provincia y ciudad se parecen, pero el patrón del repo prefiere la repetición explícita a la abstracción.

---

## Parte 2 — CSS reutilizable

### 2.1 Cómo está hoy

**Lo que carga `templates/base.html` en todas las pantallas:**
1. Tema `assets_riz`: `bootstrap.min.css`, `app.min.css`, `icons.min.css`.
2. `static/base_adicional.css` (807 líneas: sobreescribe `--bs-*`, botones, cards, badges y tablas).
3. `static/base_tablas.css` (350).
4. `css/pwa/install_bar.css`, `css/pwa/push_optin.css`, `css/core/sin_sidebar.css`, `css/core/interaccion.css` y `css/core/menu_perfil.css`.
5. Las librerías: SweetAlert2, Select2, Dropify y Fancybox.

**CSS por pantalla (uno por plantilla):**

| Archivo | Líneas | Usado en | Clases sin uso |
|---|---|---|---|
| `static/stylenew/panel_principal.css` | 958 | `seguridad/index_adm.html` | **86 de 116** (era el panel CNE) |
| `static/stylenew/docs_plataforma.css` | 347 | **ninguna** | todo (la documentación se quitó) |
| `static/base_adicional.css` | 807 | base | **92 de 120** (`badge-*` y helpers de Bootstrap 4) |
| `static/base_tablas.css` | 350 | base | **21 de 24** (`table-*` heredados) |
| `static/css/autenticacion/listado_cards.css` | 270 | usuarios | 24 de 37 (`ficha-kpi`, `hc-kpi`) |
| `static/css/core/interaccion.css` | 123 | base | 8 de 16 (`io-esqueleto`, `io-fallo` no se usan hoy) |
| `static/css/public/auth.css` | 457 | login | 1 |
| `static/css/public/publico.css` | 192 | páginas legales | 4 |
| `static/css/seguridad/crons.css` | 104 | crons | 2 |
| `static/stylenew/modulogrupo.css`, `modulossistema.css`, `perfilpanel.css`, `webpush_broadcast.css` | 47–103 | 1 pantalla c/u | 0 |

**Problemas medidos:**
- **Carpeta fuera de convención:** `static/stylenew/` (6 archivos). La regla es `static/css/<app>/`.
- **Colores sueltos sin tokens:** el azul principal aparece como `#2563eb` (13 veces, azul de Tailwind en `panel_principal.css`), `#0d6efd` (Bootstrap) y `#0081c1`; los grises, como `#6b7280`, `#9ca3af`, `#e5e7eb` y `#6c757d`, en distintos archivos. Solo `base_adicional.css` (`--bs-*`) y los públicos (`--app-*`) usan variables.
- **CSS muerto:** unas 230 clases definidas que ninguna plantilla ni JS usa, más un archivo entero (`docs_plataforma.css`).
- **`<style>` dentro de plantillas** (prohibido por `CLAUDE.md`), en 11 archivos:
  - Errores: `403.html`, `404.html`, `500.html`, `paginacion.html`.
  - Usuarios: `autenticacion/usuario/form.html`.
  - Configuración: `seguridad/configuracion/form.html`, `form_terminos.html`.
  - Módulos por grupo: `seguridad/modulogrupo/form.html`, `listado_arbol.html`.
  - Notificaciones: `seguridad/notificaciones/listado.html`.
  - Correo: `email/emailbase.html`. En correos el CSS en línea es obligatorio; ese caso no aplica.
- **83 atributos `style="..."`** en plantillas; la mayoría en `base.html`, `perfil.html` y los correos.
- **Dos sistemas de versionado mezclados:** `?v={{ version_css }}` (global) y `?v1.x` a mano.

### 2.2 Propuesta: tres capas

```
static/css/core/tokens.css        capa 1 — variables (marca, grises, estados, radios, sombras, tamaños)
static/css/core/componentes.css   capa 2 — piezas que se repiten entre pantallas
static/css/<app>/<pantalla>.css   capa 3 — solo lo propio de esa pantalla
```

**Capa 1 — `tokens.css`** (cargado en `base.html`, una sola fuente de color):
- **Marca de Exducere Online** según el estudio: `--marca-primario: #005082`, `--marca-acento: #67BD01`. Se mapean sobre `--bs-primary` / `--bs-primary-rgb` y `--bs-success`, así **todo Bootstrap** (botones sólidos, links, badges) toma la marca sin tocar cada pantalla.
- **Grises y texto:** `--tinta`, `--tinta-suave`, `--borde`, `--fondo`.
- **Estados de reunión, usados igual en el calendario, los tableros y los badges:** `--estado-confirmada`, `--estado-pendiente`, `--estado-en-cola`, `--estado-cerrada`, `--estado-falta-cierre`, `--estado-cancelada`.
- **Aviso por color del portal** (Prelude): `--cupo-normal`, `--cupo-pocos`, `--cupo-sin`.
- **Medidas:** radios, sombras y tamaños táctiles (`--alto-boton-portal: 56px`, `--texto-portal: 19px`).

**Capa 2 — `componentes.css`** (prefijo `ui-`; se escribe una vez y lo usan el micrositio y el panel):

| Componente | Lo usan | Hoy existe como |
|---|---|---|
| `ui-cabecera` (título + descripción + acciones de la pantalla) | Todas | Repetido en cada plantilla |
| `ui-kpi` (tarjeta de indicador con ícono, valor y nota) | Panel, Mi día, reportes | `pp-kpi` en `panel_principal.css` |
| `ui-filtros` (card de filtros sobre un listado) | Listados, Solicitudes, Búsqueda | Patrón repetido en listados |
| `ui-estado` (chip de estado con los tokens de estado) | Mi día, agenda, tablero, tabla, página de reunión | — |
| `ui-vacio` (estado vacío que invita a actuar) | Cola vacía, sin resultados, sin turnos | — |
| `ui-cargando` / `ui-error` (esqueleto y fallo) | Cargas AJAX | `io-esqueleto` / `io-fallo` (sin uso) |
| `ui-tarjeta-reunion` (hora, título, proyecto, estado, acciones) | Mi día, Mi agenda, cola, móvil | — |
| `ui-actividad` (línea de tiempo) | Página de reunión, ficha de cliente | — |
| `ui-carril` (fila por persona con espacios) | Vista de equipo, Mis turnos | — |

**Capa 3:** un archivo por pantalla con solo lo propio (por ejemplo, `css/agenda/mis_turnos.css` para la rejilla de la semana tipo). Si una regla aparece en una segunda pantalla, sube a `componentes.css`.

**Portal público (identidad aparte):** `css/public/portal.css` con sus propios tokens (`--portal-color` inyectado por portal desde la BD en un `<style>`… **no**: en un atributo `style="--portal-color: …"` sobre el `<body>`, que no es un bloque `<style>` y respeta la regla). Comparte con `publico.css` y `auth.css` la base de tipografía y tamaños grandes.

### 2.3 Reglas para que el CSS se reutilice de verdad

1. **Ningún color hexadecimal fuera de `tokens.css`** (salvo los correos, que exigen estilos en línea).
2. **Antes de crear una clase, buscar en `componentes.css`**. Si existe algo parecido, se extiende con un modificador (`ui-kpi--alerta`), no se copia.
3. **Bootstrap primero:** grid `row`/`col-*`, utilidades (`d-flex`, `gap-*`, `text-muted`) y componentes (`card`, `badge`, `btn`). Solo se escribe CSS para lo que Bootstrap no da.
4. **Botones siempre sólidos** (nunca `btn-outline-*`), sin degradados y sin glassmorphism.
5. **Sin `<style>` en plantillas y sin comentarios** en CSS, HTML y JS.
6. **Versionado:**
   - Los archivos compartidos (`tokens.css`, `componentes.css`) usan `?v={{ version_css }}` y se sube `VERSION_CSS` al cambiarlos.
   - Los de pantalla usan `?v1.x`, que se sube al editarlos.
7. **Nombres en español** (`ui-tarjeta-reunion`, `ui-estado--confirmada`), como el resto del repo.

### 2.4 Limpieza previa sugerida (antes de la app `agenda`)

| Paso | Efecto |
|---|---|
| Borrar `static/stylenew/docs_plataforma.css` | −347 líneas sin uso |
| Reducir `panel_principal.css` a las clases del panel actual y pasarlas a `componentes.css` (`ui-kpi`) | −800 líneas aprox. |
| Quitar de `base_adicional.css` y `base_tablas.css` las clases `badge-*` / `table-*` heredadas de Bootstrap 4 | −110 clases |
| Mover `static/stylenew/*` a `static/css/<app>/` y actualizar los `<link>` | Convención única |
| Sacar los `<style>` de las 10 plantillas (no correos) a sus `.css` | Cumplir `CLAUDE.md` |
| Crear `tokens.css` con la marca Exducere y reemplazar los hex sueltos | Un solo lugar para el color |

Las clases «sin uso» salen de buscarlas en plantillas y en `static/js`. Antes de borrar se revisa que no se armen con texto dinámico desde Python o JS (por ejemplo, `'badge-' + estado`).
