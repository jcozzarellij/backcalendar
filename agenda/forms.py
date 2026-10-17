from django import forms
from django.core.exceptions import ValidationError

from autenticacion.models import Usuario
from core.custom_models import FormBase, ModelFormBase
from .funciones_portal import RUTAS_RESERVADAS
from .models import (CierreCita, Cliente, Equipo, ExcepcionTurno, Feriado, MiembroEquipo, Portal, Producto, Proyecto,
                     Solicitud)


def usuarios_agenda():
    return Usuario.objects.filter(is_active=True, is_staff=True).order_by('first_name', 'last_name')


EXCLUIR_AUDITORIA = ('usuario_creacion', 'fecha_registro', 'usuario_modificacion', 'fecha_modificacion', 'status')


class ProyectoForm(ModelFormBase):
    class Meta:
        model = Proyecto
        exclude = EXCLUIR_AUDITORIA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lider'].queryset = usuarios_agenda()
        self.fields['codigo'].widget.attrs['col'] = '4'
        self.fields['nombre'].widget.attrs['col'] = '8'

    def clean_codigo(self):
        codigo = self.cleaned_data['codigo'].strip().lower()
        if Proyecto.objects.filter(status=True, codigo__iexact=codigo).exclude(id=self.instance.id or 0).exists():
            raise ValidationError('Ya existe un proyecto con este código')
        return codigo


class EquipoForm(ModelFormBase):
    class Meta:
        model = Equipo
        exclude = EXCLUIR_AUDITORIA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proyecto'].queryset = Proyecto.objects.filter(status=True)
        self.fields['lider'].queryset = usuarios_agenda()
        for campo in ('proyecto', 'nombre'):
            self.fields[campo].widget.attrs['col'] = '6'

    def clean(self):
        datos = super().clean()
        proyecto, nombre = datos.get('proyecto'), (datos.get('nombre') or '').strip()
        if proyecto and nombre and Equipo.objects.filter(
                status=True, proyecto=proyecto, nombre__iexact=nombre).exclude(id=self.instance.id or 0).exists():
            raise ValidationError({'nombre': 'Ese proyecto ya tiene un equipo con este nombre'})
        return datos


class MiembroEquipoForm(ModelFormBase):
    class Meta:
        model = MiembroEquipo
        fields = ('usuario', 'rol')

    def __init__(self, *args, equipo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.equipo = equipo
        ya = MiembroEquipo.objects.filter(status=True, equipo=equipo).values_list('usuario_id', flat=True)
        self.fields['usuario'].queryset = usuarios_agenda().exclude(id__in=list(ya))
        self.fields['usuario'].widget.attrs['col'] = '8'
        self.fields['rol'].widget.attrs['col'] = '4'


class FeriadoForm(ModelFormBase):
    class Meta:
        model = Feriado
        exclude = EXCLUIR_AUDITORIA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['equipo'].queryset = Equipo.objects.filter(status=True)
        self.fields['equipo'].help_text = 'Vacío = no laborable para todos'
        self.fields['fecha'].widget.attrs['col'] = '4'
        self.fields['nombre'].widget.attrs['col'] = '8'


class ExcepcionTurnoForm(ModelFormBase):
    class Meta:
        model = ExcepcionTurno
        fields = ('tipo', 'fecha_desde', 'fecha_hasta', 'hora_inicio', 'hora_fin', 'motivo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ('fecha_desde', 'fecha_hasta', 'hora_inicio', 'hora_fin'):
            self.fields[campo].widget.attrs['col'] = '6'
        self.fields['hora_inicio'].help_text = 'Vacío = todo el día'

    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get('fecha_desde'), datos.get('fecha_hasta')
        inicio, fin = datos.get('hora_inicio'), datos.get('hora_fin')
        if desde and hasta and hasta < desde:
            raise ValidationError({'fecha_hasta': 'Debe ser igual o posterior a la fecha inicial'})
        if bool(inicio) != bool(fin):
            raise ValidationError({'hora_fin': 'Indica las dos horas o deja ambas vacías'})
        if inicio and fin and fin <= inicio:
            raise ValidationError({'hora_fin': 'Debe ser posterior a la hora inicial'})
        if datos.get('tipo') == 'horario_especial' and not inicio:
            raise ValidationError({'hora_inicio': 'El horario especial necesita sus horas'})
        return datos


class SelectConDeshabilitadas(forms.Select):
    """Select que muestra algunas opciones deshabilitadas (las plataformas que todavía no existen)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.deshabilitadas = set()

    def create_option(self, name, value, *args, **kwargs):
        opcion = super().create_option(name, value, *args, **kwargs)
        if value in self.deshabilitadas:
            opcion['attrs']['disabled'] = True
        return opcion


class CitaRapidaForm(FormBase):
    """Agendar desde el panel (vista de equipo o cola): datos mínimos del cliente y la cita."""
    nombres = forms.CharField(label='Nombre del cliente', max_length=200, widget=forms.TextInput(attrs={'col': '6'}))
    correo = forms.EmailField(label='Correo del cliente', widget=forms.EmailInput(attrs={'col': '6'}))
    telefono = forms.CharField(label='Teléfono o WhatsApp', max_length=40, required=False,
                               widget=forms.TextInput(attrs={'col': '6'}))
    producto = forms.ModelChoiceField(label='Producto', queryset=Producto.objects.none(), required=False,
                                      widget=forms.Select(attrs={'col': '6'}))
    titulo = forms.CharField(label='Título de la cita', max_length=200, widget=forms.TextInput(attrs={'col': '12'}))
    inicio = forms.DateTimeField(label='Inicio', widget=forms.DateTimeInput(attrs={'col': '6', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
                                 input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M'])
    duracion = forms.IntegerField(label='Duración (min)', min_value=10, max_value=240, initial=40,
                                  widget=forms.NumberInput(attrs={'col': '6'}))
    plataforma = forms.ChoiceField(label='Videollamada en', initial='google', required=False,
                                   widget=SelectConDeshabilitadas(attrs={'col': '12'}),
                                   help_text='Se genera en la cuenta de quien organiza. Si la plataforma está caída, la cita '
                                             'se crea igual y el enlace llega al reconectar.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .funciones_reuniones import IMPLEMENTADAS
        from .models import PLATAFORMA_REUNION
        self.fields['producto'].queryset = Producto.objects.filter(status=True, activo=True).select_related('padre')
        self.fields['producto'].widget.attrs['class'] = 'select2'
        self.fields['plataforma'].choices = [(k, v if k in IMPLEMENTADAS else f'{v} (próximamente)') for k, v in PLATAFORMA_REUNION]
        self.fields['plataforma'].widget.deshabilitadas = {k for k, _ in PLATAFORMA_REUNION if k not in IMPLEMENTADAS}
        self.fields['plataforma'].widget.attrs['class'] = 'select2'

    def clean_plataforma(self):
        valor = self.cleaned_data.get('plataforma') or 'google'
        if valor in self.fields['plataforma'].widget.deshabilitadas:
            raise ValidationError('Esa plataforma todavía no está disponible.')
        return valor


class ReunionForm(FormBase):
    """Reunión propia en la plataforma elegida (hoy Google Calendar), creada o editada desde Mi agenda."""
    titulo = forms.CharField(label='Título', max_length=200, widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Ej.: Revisión semanal con el equipo'}))
    inicio = forms.DateTimeField(label='Inicio', widget=forms.DateTimeInput(attrs={'col': '6', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
                                 input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M'])
    duracion = forms.IntegerField(label='Duración (min)', min_value=5, max_value=720, initial=30,
                                  widget=forms.NumberInput(attrs={'col': '6'}))
    color = forms.ChoiceField(label='Color', required=False, widget=forms.Select(attrs={'col': '6'}))
    lugar = forms.CharField(label='Lugar', max_length=300, required=False,
                            widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Oficina, dirección o enlace'}))
    invitados = forms.CharField(label='Invitados', required=False,
                                widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'correo@ejemplo.com, otro@ejemplo.com'}),
                                help_text='Correos separados por coma. Google les envía la invitación.')
    descripcion = forms.CharField(label='Descripción', required=False, widget=forms.Textarea(attrs={'col': '12', 'rows': '3'}))
    meet = forms.BooleanField(label='Agregar videollamada de Google Meet', required=False, initial=True,
                              widget=forms.CheckboxInput(attrs={'col': '12'}))

    def __init__(self, *args, todo_el_dia=False, creando=True, **kwargs):
        super().__init__(*args, **kwargs)
        from .funciones_google import COLORES_EVENTO
        self.fields['color'].choices = [('', 'Color del calendario')] + [(k, nombre) for k, (nombre, _) in COLORES_EVENTO.items()]
        self.fields['color'].widget.attrs['class'] = 'select2'
        if todo_el_dia:
            del self.fields['inicio'], self.fields['duracion']
        if not creando:
            del self.fields['meet']

    def clean_invitados(self):
        from django.core.validators import validate_email
        correos = [c.strip() for c in (self.cleaned_data.get('invitados') or '').replace(';', ',').split(',') if c.strip()]
        malos = []
        for correo in correos:
            try:
                validate_email(correo)
            except ValidationError:
                malos.append(correo)
        if malos:
            raise ValidationError('Correo no válido: ' + ', '.join(malos))
        return list(dict.fromkeys(correos))


class SolicitudForm(ModelFormBase):
    class Meta:
        model = Solicitud
        fields = ('cliente', 'producto', 'proyecto', 'motivo', 'mensaje', 'origen', 'telefono_para_llamar')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = Cliente.objects.filter(status=True)
        self.fields['producto'].queryset = Producto.objects.filter(status=True, activo=True)
        self.fields['proyecto'].queryset = Proyecto.objects.filter(status=True, activo=True)
        for campo in ('cliente', 'producto', 'proyecto', 'origen', 'telefono_para_llamar'):
            self.fields[campo].widget.attrs['col'] = '6'


class CierreCitaForm(ModelFormBase):
    class Meta:
        model = CierreCita
        fields = ('resumen', 'tipo_reunion', 'asistio', 'pidio_proforma', 'fue_soporte', 'es_lead')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resumen'].widget.attrs['rows'] = '4'
        self.fields['tipo_reunion'].widget.attrs['col'] = '6'
        for campo in ('asistio', 'pidio_proforma', 'fue_soporte', 'es_lead'):
            self.fields[campo].widget.attrs['col'] = '3'


class PortalForm(ModelFormBase):
    class Meta:
        model = Portal
        exclude = EXCLUIR_AUDITORIA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ('nombre', 'slug', 'color_principal', 'telefono_atencion'):
            self.fields[campo].widget.attrs['col'] = '6'
        self.fields['sitios_autorizados'].widget.attrs['rows'] = '3'

    def clean_slug(self):
        slug = self.cleaned_data['slug'].strip().lower()
        if Portal.objects.filter(status=True, slug=slug).exclude(id=self.instance.id or 0).exists():
            raise ValidationError('Ya existe un portal con esta ruta')
        return slug


class ProductoForm(ModelFormBase):
    class Meta:
        model = Producto
        exclude = EXCLUIR_AUDITORIA + ('portal',)

    def __init__(self, *args, portal=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = portal
        self.fields['padre'].queryset = Producto.objects.filter(status=True, portal=portal, padre__isnull=True).exclude(
            id=self.instance.id or 0)
        self.fields['equipo'].queryset = Equipo.objects.filter(status=True, activo=True).select_related('proyecto')
        for campo in ('slug', 'padre', 'equipo', 'sitio_web', 'nombre', 'nombre_en', 'nombre_pt'):
            self.fields[campo].widget.attrs['col'] = '6'
        for campo in ('duracion_min', 'antelacion_horas', 'margen_min', 'limite_dia', 'limite_semana', 'ventana_dias', 'orden'):
            self.fields[campo].widget.attrs['col'] = '3'
        for campo in ('activo', 'destacado'):
            self.fields[campo].widget.attrs['col'] = '6'

    def clean(self):
        datos = super().clean()
        slug, padre = (datos.get('slug') or '').strip().lower(), datos.get('padre')
        if padre and padre.padre_id:
            raise ValidationError({'padre': 'Solo hay dos niveles: un subproducto no puede tener hijos'})
        repetido = Producto.objects.filter(status=True, portal=self.portal, padre=padre, slug=slug).exclude(id=self.instance.id or 0)
        if slug in RUTAS_RESERVADAS:
            raise ValidationError({'slug': 'Esta ruta está reservada por el sistema, elija otra'})
        if slug and repetido.exists():
            raise ValidationError({'slug': 'Ya existe un producto con esta ruta en el portal'})
        datos['slug'] = slug
        return datos


class ReservaPublicaForm(FormBase):
    """Datos que el cliente llena en el portal público (paso 3) o al pedir que le llamen."""
    nombres = forms.CharField(label='Nombre y apellido', max_length=200)
    correo = forms.EmailField(label='Correo')
    telefono = forms.CharField(label='Teléfono o WhatsApp', max_length=40, required=False)
    mensaje = forms.CharField(label='¿Sobre qué quiere conversar?', max_length=2000, required=False,
                              widget=forms.Textarea)
    inicio = forms.DateTimeField(label='Horario', required=False, input_formats=['%Y-%m-%dT%H:%M'])

    def __init__(self, *args, **kwargs):
        self.requiere_inicio = kwargs.pop('requiere_inicio', True)
        self.requiere_telefono = kwargs.pop('requiere_telefono', False)
        super().__init__(*args, **kwargs)
        self.fields['inicio'].required = self.requiere_inicio
        self.fields['telefono'].required = self.requiere_telefono

    def clean_nombres(self):
        nombres = ' '.join(self.cleaned_data['nombres'].split())
        if len(nombres) < 3:
            raise ValidationError('Escriba su nombre completo.')
        return nombres

    def primer_error(self):
        for campo, errores in self.errors.items():
            etiqueta = self.fields[campo].label if campo in self.fields else ''
            return f'{etiqueta}: {errores[0]}' if etiqueta else errores[0]
        return 'Revise los datos.'


class BuscarCitaForm(FormBase):
    """«Ver mi cita»: el cliente abre su cita con el código y el correo con el que agendó."""
    codigo = forms.CharField(max_length=20)
    correo = forms.EmailField()

    def clean_codigo(self):
        from .funciones_citas import normalizar_codigo_cita
        return normalizar_codigo_cita(self.cleaned_data['codigo'])


class ClienteForm(ModelFormBase):
    class Meta:
        model = Cliente
        fields = ('nombres', 'correo', 'telefono', 'idioma', 'portal_origen', 'nota_privada')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['portal_origen'].queryset = Portal.objects.filter(status=True)
        self.fields['portal_origen'].required = False
        self.fields['nota_privada'].widget.attrs['rows'] = '3'
        for campo in ('nombres', 'correo', 'telefono', 'idioma', 'portal_origen'):
            self.fields[campo].widget.attrs['col'] = '6'

    def clean_correo(self):
        correo = self.cleaned_data['correo'].strip().lower()
        if Cliente.objects.filter(status=True, correo__iexact=correo).exclude(id=self.instance.id or 0).exists():
            raise ValidationError('Ya existe un cliente con este correo')
        return correo
