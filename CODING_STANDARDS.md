# CODING_STANDARDS — backend

Skills de capa (`django-backend`, `formmodal`, `batch-process`, `inline-ajax-autosave`, `/crud-simple`) amplían estas reglas; este archivo manda.

## Views: patrón `if action`

Referencia canónica: `area_geografica/view_pais.py`, `autenticacion/adm_usuario.py`.

1. `data = {...}` + `addData(request, data)` al inicio.
2. `if request.method == 'POST':` → `action = request.POST['action']` → `try/except` con `if action == '...': elif ...`. El código de cada acción va inline en su rama.
3. `elif request.method == 'GET':` → `if 'action' in request.GET:` (formularios, JSON) → listado y `render`.

- La clave es `action` (no `accion`) en POST y GET.
- Lógica de dominio reutilizable: `funciones_<app>.py` (o `core/funciones_adicionales.py`), importada desde la view, como `habilitar_acceso_administrativo` en `autenticacion/funciones_autenticacion.py`. El CRUD directo queda inline.
- Consultas GET compartidas entre pantallas (hoy `consultarusername`, `consultarcedula`): rama `accion` en `core.ajax.ConsultasAjax`, ruta `/ajaxrequest/<accion>`.
- Catálogos de textos o guías: tabla detalle (modelo + seeder en `scripts/`).

## Modelos

Todo modelo hereda de `core.custom_models.ModeloBase`, que da `id`, `usuario_creacion`, `fecha_registro`, `usuario_modificacion`, `fecha_modificacion`, `status` y `save(request)`.

- Reusar esos campos en vez de redeclarar equivalentes: `fecha_registro` (no `fecha`, `creado_en`, `created_at`, `fecha_creacion`), `fecha_modificacion` (no `actualizado_en`, `modificado_en`), `usuario_creacion` / `usuario_modificacion` (no `creado_por`, `editado_por`, `modificado_por`).
- `activo`/`activa` convive con `status`: `status` es borrado lógico, `activo` es encendido/en pausa.
- Excepción: logs append-only (`ErrorLog`, `AudiUsuarioTabla`, `CronLogEjecucion`, `SessionUser`), que lo declaran en su docstring. Excepciones nuevas, solo si se piden.
- Choices: constante a nivel de módulo, fuera de la clase (ej. `PRIORIDAD_NOTIFICACION` en `seguridad/models.py`); el campo usa `choices=CONSTANTE`.

## Soft delete

Baja = `filtro.status = False; filtro.save(request)`; sin `.delete()`. Listados filtran `Q(status=True)`. `status` nunca se muestra (columna, helper, campo de form).

Trampa: en `get_or_create` / `update_or_create` con clave única (OneToOne o `UniqueConstraint`), `status` va en `defaults` (reactiva la fila dada de baja), no en la búsqueda. El filtro `status=True` es para lecturas.

## Uploads

Todo `FileField`/`ImageField` declara en el modelo `FileExtensionValidator` más un validador de tamaño de `core/validadores.py` (`validate_file_size_2mb`, `_3mb`, `_20mb`, …). Validar en `add` y `change`; las extensiones permitidas se infieren del `FileExtensionValidator` del modelo.
