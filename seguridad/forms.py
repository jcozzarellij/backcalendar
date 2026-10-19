import re

from django import forms
from django.contrib.auth.models import Group
from django.db.models import Value
from django.db.models.functions import Concat

from core.custom_models import ModelFormBase
from seguridad.models import Configuracion, DominioCorreoPermitido, Modulo, ModuloGrupo, GroupModulo


class ConfiguracionForm(ModelFormBase):
    class Meta:
        model = Configuracion
        exclude = ('usuario_modificacion', 'fecha_modificacion', 'usuario_creacion', 'terminosycondiciones',)

    def __init__(self, *args, **kwargs):
        super(ConfiguracionForm, self).__init__(*args, **kwargs)
        self.fields["ico"].widget.attrs['data-default-file'] = self.instance.ico.url if self.instance.ico else ""
        self.fields["logo_sistema"].widget.attrs['data-default-file'] = self.instance.logo_sistema.url if self.instance.logo_sistema else ""
        self.fields["logo_sistema_white"].widget.attrs['data-default-file'] = self.instance.logo_sistema_white.url if self.instance.logo_sistema_white else ""
        self.fields["fondo_landing"].widget.attrs['data-default-file'] = self.instance.fondo_landing.url if self.instance.fondo_landing else ""
        for campo_imagen in ('ico', 'logo_sistema', 'logo_sistema_white', 'fondo_landing'):
            if campo_imagen in self.fields:
                self.fields[campo_imagen].widget.attrs['data-allowed-file-extensions'] = "jpg jpeg png tiff webp jfif"
                self.fields[campo_imagen].widget.attrs['data-max-file-size'] = "8M"

        for campo in ('pg_dump_cmd', 'backup_retencion'):
            if campo in self.fields:
                self.fields[campo].required = False

        for k, v in self.fields.items():
            if k in ('ico', 'logo_sistema', 'logo_sistema_white', 'fondo_landing', 'direccion', 'nombre_empresa', 'alias', 'descripcion', 'telefono', 'email',  'email_notificacion', 'web', 'titulo', 'pg_dump_cmd', 'backup_retencion',):
                self.fields[k].widget.attrs['col'] = "6"
            if k == 'telefono':
                # Formato telefónico real: dígitos + prefijo internacional, paréntesis,
                # espacios y guiones. El pattern «solo dígitos» rechazaba el valor YA guardado
                # «(+593) 995395166» y el navegador bloqueaba el submit del form entero.
                self.fields[k].widget.attrs['pattern'] = r"[\d\s()+\-]*"
                self.fields[k].widget.attrs['title'] = "Números, espacios, + ( ) -"

        for k in CAMPOS_CONEXIONES:
            if k in self.fields:
                self.fields[k].widget.attrs['col'] = "6"
                self.fields[k].widget.attrs['autocomplete'] = "off"
        for k in SECRETOS_CONEXIONES:
            if k in self.fields:
                attrs = dict(self.fields[k].widget.attrs)
                attrs.pop('rows', None)
                attrs['autocomplete'] = "new-password"
                attrs['placeholder'] = "••••••••" if getattr(self.instance, k, '') else "Pega aquí el secreto"
                self.fields[k].widget = forms.PasswordInput(render_value=False, attrs=attrs)
        self.campos_secretos = SECRETOS_CONEXIONES
        self.secretos_guardados = [k for k in SECRETOS_CONEXIONES if getattr(self.instance, k, '')]

    def clean(self):
        datos = super().clean()
        for k in SECRETOS_CONEXIONES:
            if k in datos and not (datos.get(k) or '').strip():
                datos[k] = getattr(self.instance, k, '') or ''
        for k in CAMPOS_CONEXIONES:
            if isinstance(datos.get(k), str):
                datos[k] = datos[k].strip()
        return datos


SECRETOS_CONEXIONES = ('google_client_secret', 'teams_client_secret', 'zoom_client_secret')
CAMPOS_CONEXIONES = ('google_client_id', 'google_client_secret', 'google_redirect_uri',
                     'teams_client_id', 'teams_client_secret', 'teams_tenant_id', 'teams_redirect_uri',
                     'zoom_client_id', 'zoom_client_secret', 'zoom_redirect_uri')


class ConfiguracionTerminosForm(ModelFormBase):
    class Meta:
        model = Configuracion
        fields = ('terminosycondiciones',)

    def __init__(self, *args, **kwargs):
        super(ConfiguracionTerminosForm, self).__init__(*args, **kwargs)


class ModuloForm(ModelFormBase):
    class Meta:
        model = Modulo
        exclude = ( 'usuario_modificacion', 'fecha_modificacion', 'usuario_creacion', 'fecha_registro', 'status')


class GroupForm(ModelFormBase):
    class Meta:
        model = Group
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        self.fields['permissions'].queryset = self.fields['permissions'].queryset.\
            annotate(full_name_db=Concat('content_type__app_label', Value('__'), 'content_type__model')).\
            exclude(full_name_db__in=['sessions__session', 'auth__permission', 'contenttypes__contenttype',
                                     'admin__logentry', 'authtoken__token', 'seguridad__usuarioconectado', 'seguridad__carousel', 'seguridad__redsocial', 'seguridad__errorlog', 'seguridad__audiusuariotabla',
                                     'background_task__completedtask', 'background_task__task', 'webpush__subscriptioninfo',
                                      'webpush__pushinformation', 'webpush__group', 'authtoken__tokenproxy', 'ventas__pedidodetalle',
                                      'autenticacion__codigo', 'seguridad__usuarionotificacion', 'seguridad__sessionuser']).\
            exclude(content_type__app_label__in=("dobra", "reportes"))

        for k, v in self.fields.items():
            self.fields[k].widget.attrs['col'] = "12"

class ModuloGrupoForm(ModelFormBase):
    class Meta:
        model = ModuloGrupo
        exclude = ( 'usuario_modificacion', 'fecha_modificacion', 'usuario_creacion', 'fecha_registro', 'status')

    def __init__(self, *args, **kwargs):
        kwargs["no_requeridos"] = ["modulos"]
        super(ModuloGrupoForm, self).__init__(*args, **kwargs)
        self.fields['modulos'].queryset = self.fields['modulos'].queryset.order_by('orden')
        self.fields['modulos'].widget = forms.HiddenInput()
        self.initial["modulos"] = ""


class GroupModuloForm(ModelFormBase):
    class Meta:
        model = GroupModulo
        exclude = ('usuario_modificacion', 'fecha_modificacion', 'usuario_creacion', 'fecha_registro', 'status')

    def __init__(self, *args, **kwargs):
        kwargs["no_requeridos"] = ["modulos", "group"]
        super(GroupModuloForm, self).__init__(*args, **kwargs)
        self.fields['modulos'].queryset = self.fields['modulos'].queryset.order_by('orden')
        self.fields["group"].widget = forms.HiddenInput()
        self.fields["group"].required = False  # ✅ también puedes ponerlo explícito por si acaso


DOMINIO_VALIDO = re.compile(r'^(?=.{3,150}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$')


class DominioCorreoPermitidoForm(ModelFormBase):
    class Meta:
        model = DominioCorreoPermitido
        exclude = ('usuario_modificacion', 'fecha_modificacion', 'usuario_creacion', 'fecha_registro', 'status')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['dominio'].widget.attrs['col'] = '8'
        self.fields['activo'].widget.attrs['col'] = '4'

    def clean_dominio(self):
        dominio = DominioCorreoPermitido.normalizar(self.cleaned_data.get('dominio'))
        if not DOMINIO_VALIDO.match(dominio):
            raise forms.ValidationError('Escribe un dominio válido, sin @. Ej.: excudere.com')
        repetido = DominioCorreoPermitido.objects.filter(dominio=dominio, status=True)
        if self.instance.pk:
            repetido = repetido.exclude(pk=self.instance.pk)
        if repetido.exists():
            raise forms.ValidationError('Ese dominio ya está registrado.')
        return dominio
