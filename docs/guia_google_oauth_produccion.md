# Guía: configurar Google (Calendar + inicio de sesión) en producción

Esta guía es para quien hace el deploy. Turno usa **un solo cliente OAuth de Google** para dos cosas:

| Uso | Para qué | URL de retorno |
|---|---|---|
| Google Calendar | Cada persona del equipo conecta su calendario (crear citas con Meet, ver libre/ocupado) | `https://<dominio>/agenda/aplicaciones/google/` |
| Inicio de sesión | Botón «Continuar con Google» en `/login/` | `https://<dominio>/login/google/callback/` |

`<dominio>` es exactamente el host de `BACKEND_PUBLIC_URL` en el `credenciales.json` de producción (por ejemplo, si
`BACKEND_PUBLIC_URL` es `https://turno.tudominio.com`, las URLs son `https://turno.tudominio.com/agenda/aplicaciones/google/`
y `https://turno.tudominio.com/login/google/callback/`).

Las claves **no** van en `credenciales.json`: se cargan desde el panel, en **Configuración del sitio → Conexión Google**.

---

## 1. Proyecto en Google Cloud

1. Entrar a <https://console.cloud.google.com/> con la cuenta de Google que administrará la app.
2. Arriba a la izquierda, en el selector de proyectos: **Proyecto nuevo** → nombre `Turno` (o usar uno existente de la empresa).
3. Dejar ese proyecto seleccionado para todos los pasos siguientes.

## 2. Habilitar la API de Google Calendar

1. Menú **APIs y servicios → Biblioteca**.
2. Buscar **Google Calendar API** → abrirla → **Habilitar**.

No hace falta habilitar otra API: el inicio de sesión usa OpenID Connect, que viene incluido.

## 3. Pantalla de consentimiento (Google Auth Platform)

Menú **Google Auth Platform** (en consolas antiguas: **APIs y servicios → Pantalla de consentimiento de OAuth**).

### 3.1 Desarrollo de la marca (Branding)

- **Nombre de la app:** `Turno` (es lo que verá la persona al elegir su cuenta).
- **Correo de asistencia del usuario:** un correo de soporte de la empresa.
- **Logo:** opcional.
- **Dominios autorizados:** agregar el dominio raíz de producción (ej. `tudominio.com`).
- **Página principal / Política de privacidad:** `https://<dominio>/` y `https://<dominio>/privacidad/`.
- **Correo del desarrollador:** el de quien mantiene el sistema.

### 3.2 Público (Audience)

| Tipo | Cuándo elegirlo |
|---|---|
| **Externo** | Si van a entrar correos de varios dominios o `@gmail.com`. **Recomendado.** |
| Interno | Solo si todas las cuentas son del mismo Google Workspace de la empresa. Con este tipo no entran correos de otros dominios. |

Si es **Externo**, la app nace en estado **Prueba**: solo pueden autorizar los correos cargados en **Usuarios de prueba**
(máximo 100). Para que entre cualquiera, pulsar **Publicar aplicación**.

> Con la app publicada y los permisos de Calendar, Google puede pedir una verificación de la app. Mientras tanto
> muestra el aviso «Google no ha verificado esta app»; se puede continuar desde **Configuración avanzada**.

### 3.3 Acceso a los datos (Data access / Scopes)

**Agregar o quitar permisos** y marcar:

- `openid`
- `.../auth/userinfo.email`
- `.../auth/userinfo.profile`
- `.../auth/calendar.events`
- `.../auth/calendar.freebusy`
- `.../auth/calendar.calendarlist.readonly`

Guardar.

## 4. Crear el cliente OAuth y registrar las URLs

1. **Google Auth Platform → Clientes → Crear cliente** (en consolas antiguas: **Credenciales → Crear credenciales → ID de
   cliente de OAuth**).
2. **Tipo de aplicación:** `Aplicación web`.
3. **Nombre:** `Turno producción`.
4. **Orígenes de JavaScript autorizados:** dejar vacío (no se usa).
5. **URI de redireccionamiento autorizados** → **Agregar URI**, una por línea:

   ```
   https://<dominio>/agenda/aplicaciones/google/
   https://<dominio>/login/google/callback/
   ```

   Copiarlas tal cual: con `https://`, sin `www` si `BACKEND_PUBLIC_URL` no lo tiene, y **con la `/` final**.
6. **Crear**. Google muestra el **ID de cliente** (termina en `.apps.googleusercontent.com`) y el **Secreto del cliente**.
   Copiarlos; el secreto solo se puede descargar en ese momento (después se genera uno nuevo si se pierde).

Los cambios de URIs pueden tardar desde unos minutos hasta algunas horas en aplicarse.

## 5. Cargar las claves en Turno

1. Entrar al panel de producción con el usuario `admin`.
2. **Configuración del sitio → pestaña Conexión Google**:
   - **ID de cliente de Google:** el ID del paso 4.
   - **Secreto de cliente de Google:** el secreto del paso 4 (se guarda cifrado).
   - **URI de redirección de Google:** dejar **vacío** (el sistema usa `https://<dominio>/agenda/aplicaciones/google/`).
   - **Permitir inicio de sesión con Google:** activarlo si se quiere el botón en `/login/`.
3. **Guardar**.
4. La nota azul de esa pestaña muestra las dos URLs que calcula el sistema: **deben coincidir letra por letra** con las
   registradas en Google.
5. Para el inicio de sesión: **Configuración → Dominios de correo** → **Nuevo dominio** (ej. `tudominio.com` o
   `gmail.com`). Sin dominios cargados nadie entra con Google.

> No cambiar `SECRET_KEY` de producción después de cargar el secreto: con otra clave el secreto guardado deja de
> poder leerse y hay que volver a cargarlo.

## 6. Probar

**Calendar**
1. Con un usuario del equipo: **Agenda → Conexiones → Conectar con Google**.
2. Elegir la cuenta, aceptar permisos → vuelve a Conexiones con la cuenta conectada.
3. **Probar conexión** debe responder bien.

**Inicio de sesión**
1. El usuario debe existir en Turno con el **mismo correo** en su campo Email, y ese dominio debe estar permitido.
2. En `/login/` → **Continuar con Google** → elegir la cuenta → entra a `/panel/`.
3. En **Dominios de correo → Cuentas vinculadas** aparece la cuenta con su último acceso.

## 7. Errores comunes

| Error | Causa y solución |
|---|---|
| `redirect_uri_mismatch` | La URI registrada no es idéntica a la del sistema (falta `/` final, `http` vs `https`, `www`). Compararla con la nota de Configuración. Si recién se cambió, esperar. |
| `access_denied` / «acceso bloqueado» | App en modo **Prueba** y el correo no está en Usuarios de prueba, o el público es **Interno** y el correo es de otro dominio. |
| «Google no ha verificado esta app» | Normal mientras la app no está verificada. Continuar desde Configuración avanzada o pedir la verificación en Google. |
| «Google no entregó el token de renovación» (Calendar) | Quitar el acceso de Turno en <https://myaccount.google.com/permissions> y volver a conectar. |
| «No hay una cuenta asociada a este correo» (login) | Ningún usuario activo de Turno tiene ese email. |
| «Los correos de ese dominio no pueden iniciar sesión con Google» | Falta el dominio en Dominios de correo o está pausado. |
| «Este correo pertenece a más de un usuario» | Dos usuarios tienen el mismo email; corregirlo en Usuarios. |
| «La solicitud no coincide con tu sesión» | Se abrió el login en un host y Google volvió a otro (ej. con y sin `www`). Usar siempre el dominio de `BACKEND_PUBLIC_URL`. |

## Resumen para enviar

> Hola. En Google Cloud (proyecto Turno): habilita **Google Calendar API**; en **Google Auth Platform** configura la
> marca, público **Externo** y los permisos `openid`, `userinfo.email`, `userinfo.profile`, `calendar.events`,
> `calendar.freebusy` y `calendar.calendarlist.readonly`. Crea un cliente OAuth **Aplicación web** con estas URIs de
> redireccionamiento:
>
> - `https://<dominio>/agenda/aplicaciones/google/`
> - `https://<dominio>/login/google/callback/`
>
> Pásame el ID de cliente y el secreto (o cárgalos tú en Turno → Configuración del sitio → Conexión Google).
> El dominio debe ser exactamente el de `BACKEND_PUBLIC_URL`.
