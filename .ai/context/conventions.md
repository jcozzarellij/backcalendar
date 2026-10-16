# Code Conventions — backcalendar

## Idioma

Todo el código en **español**: modelos, campos, funciones, variables, comentarios.
**Excepciones:** built-ins Django, APIs de terceros, archivos de configuración.

---

## Naming

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Modelos | PascalCase, singular | `AgentesIA`, `Empresa`, `Movimiento` |
| Campos | snake_case descriptivo | `fecha_registro`, `saldo_creditos` |
| Foreign keys | sustantivo singular | `perfil`, `empresa`, `agente` |
| ManyToMany | sustantivo plural | `apikey`, `notificar_a` |
| Booleanos | prefijo `es_` / `tiene_` | `es_activo`, `activo` |
| Funciones/métodos | snake_case verbo-primero | `debitar`, `acreditar`, `regenerar_webservice_token` |
| Vistas | `accion_sustantivo` | `entrenamiento_ia_view`, `chat_agente_view` |
| Variables | snake_case sin abrev | `lista_agentes` no `a` |
| Constantes | UPPER_SNAKE_CASE | `MODELOS_DISPONIBLES`, `PROVEEDOR_CHOICES` |
| URLs | minúsculas-con-guiones | `agentes-ia/entrenamiento/` |
| Templates | snake_case + sufijo | `agente_listado.html` |

---

## Sufijos templates

| Sufijo | Propósito |
|--------|-----------|
| `*_listado.html` | Listado DataTables |
| `*_form.html` | Crear/editar (modal o página) |
| `*_detalle.html` | Vista solo lectura |

---

## Estructura de vista

Orden por convención:

1. Decoradores: `@login_required`, `@secure_module`
2. Inicializar `data = {'titulo':..., 'modulo':..., 'ruta': request.path}`
3. `addData(request, data)`
4. Branches por `request.method`
5. Queries con `select_related` / `prefetch_related`
6. `data['x'] = ...; return render(...)`

> Ver ejemplos reales en `area_geografica/view_pais.py` y `autenticacion/adm_usuario.py`.

---

## Estructura modelo

Orden:

1. Choices (constantes a nivel módulo o atributo de clase)
2. Campos simples
3. Relaciones (FK, M2M)
4. `class Meta` con `verbose_name`, `ordering`
5. `__str__`
6. Métodos custom
7. `@property`

**Heredar siempre `ModeloBase`** y filtrar `status=True` en queries.

---

## Estructura form

Forms heredan de `ModelFormBase` (`core/custom_forms.py`).
Orden: `Meta` → `__init__` override → `clean_<field>` → `clean()`.

---

## Orden imports

1. Standard library
2. Django
3. Terceros (`for_django_projects`, `webpush`, `cryptography`, etc.)
4. Apps locales (`core.*`, otras apps)
5. Imports relativos (`.models`, `.forms`)

---

## Estructura archivos por app

```
app_name/
├── models.py              # único si < 200 líneas
├── models/                # split por dominio si > 200
├── view_<feature>.py      # un archivo por dominio funcional
├── public_<feature>.py    # vistas públicas (sin login)
├── forms.py
├── urls.py                # lista de dicts (registrada en backcalendar/urls.py)
├── services.py            # integraciones externas / lógica transaccional
└── utils.py
```

---

## Comentarios

- **Docstrings** en funciones no triviales: 1 línea + Args/Returns si complejo
- **Inline** explica *por qué*, nunca *qué*
- No `print()` en código commit (usar `logger`)

---

## Errores

`try/except` con tipos específicos primero, `Exception` como fallback genérico.
Logging con `logger = logging.getLogger(__name__)`.

---

## CSS

CSS específico de página → archivo en `static/css/<django-app>/<pagina>.css` (ver CLAUDE.md).
**Nunca** CSS inline en templates ni `<style>` en `block head`.

---

## JavaScript

- Funciones de negocio en español: `guardarAgente()`, `enviarPrueba()`
- Helpers genéricos jQuery/DataTables pueden usar inglés: `initDataTable()`
- Variables en español; no nombres de una letra fuera de loops
- SweetAlert2: sintaxis **legacy** (ver `skills/sweetalert-legacy.md`)

---

## Configuración

Secretos en `credenciales.json` (gitignored). Nunca hardcodear ni commitear.
Lectura en `../../backcalendar/settings.py`.

---

## Skills de Claude Code instaladas

Guías de referencia en `.claude/skills/` que Claude Code carga solo mientras trabaja en la terminal; no son código de la app.
