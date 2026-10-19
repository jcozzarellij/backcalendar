from datetime import date, datetime, time, timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase

from autenticacion.models import Usuario
from . import funciones_google
from .funciones_permisos import (ROL_ADMIN_PROYECTOS, ROL_ADMINISTRADOR, equipos_visibles, es_lider_equipo,
                                 puede_editar_turnos_de)
from .funciones_turnos import aplicar_semana_tipo, celdas_a_franjas, franjas_a_celdas, franjas_del_dia, patron_vigente
from .models import ConexionAplicacion, Equipo, ExcepcionTurno, Feriado, FranjaTurno, MiembroEquipo, PatronTurno, Proyecto


def crear_usuario(username):
    return Usuario.objects.create_user(username=username, password='x', first_name=username.title(),
                                       last_name='Prueba', is_staff=True, direccion='-')


class TurnosTests(TestCase):
    def setUp(self):
        self.ana = crear_usuario('ana')
        self.lunes = date(2026, 10, 12)
        patron = PatronTurno.objects.create(usuario=self.ana, vigencia_desde=date(2026, 10, 1))
        FranjaTurno.objects.create(patron=patron, dia_semana=0, hora_inicio=time(8, 0), hora_fin=time(12, 0))
        FranjaTurno.objects.create(patron=patron, dia_semana=0, hora_inicio=time(14, 0), hora_fin=time(17, 0))

    def test_franjas_del_dia_devuelve_el_patron(self):
        self.assertEqual(franjas_del_dia(self.ana, self.lunes), [(time(8, 0), time(12, 0)), (time(14, 0), time(17, 0))])
        self.assertEqual(franjas_del_dia(self.ana, self.lunes + timedelta(days=1)), [])

    def test_feriado_general_anula_el_dia(self):
        Feriado.objects.create(fecha=self.lunes, nombre='Prueba')
        self.assertEqual(franjas_del_dia(self.ana, self.lunes), [])

    def test_excepcion_de_todo_el_dia_anula(self):
        ExcepcionTurno.objects.create(usuario=self.ana, tipo='permiso', fecha_desde=self.lunes, fecha_hasta=self.lunes)
        self.assertEqual(franjas_del_dia(self.ana, self.lunes), [])

    def test_excepcion_parcial_recorta_la_franja(self):
        ExcepcionTurno.objects.create(usuario=self.ana, tipo='permiso', fecha_desde=self.lunes, fecha_hasta=self.lunes,
                                      hora_inicio=time(9, 0), hora_fin=time(10, 0))
        self.assertEqual(franjas_del_dia(self.ana, self.lunes),
                         [(time(8, 0), time(9, 0)), (time(10, 0), time(12, 0)), (time(14, 0), time(17, 0))])

    def test_horario_especial_reemplaza(self):
        ExcepcionTurno.objects.create(usuario=self.ana, tipo='horario_especial', fecha_desde=self.lunes,
                                      fecha_hasta=self.lunes, hora_inicio=time(15, 0), hora_fin=time(18, 0))
        self.assertEqual(franjas_del_dia(self.ana, self.lunes), [(time(15, 0), time(18, 0))])

    def test_celdas_y_franjas_son_inversas(self):
        celdas = {'0': ['08:00', '08:40', '09:20', '14:00'], '2': ['10:00']}
        franjas = celdas_a_franjas(celdas, 40)
        self.assertEqual(franjas[0], [(time(8, 0), time(10, 0)), (time(14, 0), time(14, 40))])
        patron = PatronTurno.objects.create(usuario=self.ana, vigencia_desde=date(2027, 1, 1))
        for dia, lista in franjas.items():
            for inicio, fin in lista:
                FranjaTurno.objects.create(patron=patron, dia_semana=dia, hora_inicio=inicio, hora_fin=fin)
        vuelta = franjas_a_celdas(patron, 40)
        self.assertEqual(vuelta[0], ['08:00', '08:40', '09:20', '14:00'])
        self.assertEqual(vuelta[2], ['10:00'])

    def test_aplicar_semana_tipo_recorta_la_vigente(self):
        nuevo = aplicar_semana_tipo(self.ana, {0: [(time(9, 0), time(11, 0))]}, date(2026, 11, 1), date(2026, 11, 30), None)
        anterior = PatronTurno.objects.filter(status=True, usuario=self.ana).exclude(pk=nuevo.pk).order_by('vigencia_desde')
        self.assertEqual([(p.vigencia_desde, p.vigencia_hasta) for p in anterior],
                         [(date(2026, 10, 1), date(2026, 10, 31)), (date(2026, 12, 1), None)])
        self.assertEqual(patron_vigente(self.ana, date(2026, 11, 16)), nuevo)
        self.assertEqual(franjas_del_dia(self.ana, date(2026, 11, 16)), [(time(9, 0), time(11, 0))])
        self.assertEqual(franjas_del_dia(self.ana, date(2026, 12, 7)), [(time(8, 0), time(12, 0)), (time(14, 0), time(17, 0))])

    def test_aplicar_semana_tipo_sin_espacios_falla(self):
        with self.assertRaises(ValueError):
            aplicar_semana_tipo(self.ana, {0: []}, date(2026, 11, 1), None, None)


class PermisosTests(TestCase):
    def setUp(self):
        self.lider = crear_usuario('lider')
        self.jefe = crear_usuario('jefe')
        self.miembro = crear_usuario('miembro')
        self.ajeno = crear_usuario('ajeno')
        Group.objects.create(name=ROL_ADMINISTRADOR).user_set.add(self.lider)
        Group.objects.create(name=ROL_ADMIN_PROYECTOS).user_set.add(self.jefe)
        proyecto = Proyecto.objects.create(codigo='p1', nombre='Proyecto 1', lider=self.lider)
        self.equipo = Equipo.objects.create(proyecto=proyecto, nombre='Equipo X', lider=self.jefe)
        MiembroEquipo.objects.create(equipo=self.equipo, usuario=self.miembro)
        self.otro = Equipo.objects.create(proyecto=proyecto, nombre='Equipo Y')

    def test_lider_general_ve_todo(self):
        self.assertEqual(equipos_visibles(self.lider).count(), 2)
        self.assertTrue(puede_editar_turnos_de(self.lider, self.ajeno))

    def test_lider_de_equipo_solo_su_equipo(self):
        self.assertTrue(es_lider_equipo(self.jefe, self.equipo))
        self.assertFalse(es_lider_equipo(self.jefe, self.otro))
        self.assertTrue(puede_editar_turnos_de(self.jefe, self.miembro))
        self.assertFalse(puede_editar_turnos_de(self.jefe, self.ajeno))
        self.assertEqual(list(equipos_visibles(self.jefe)), [self.equipo])

    def test_miembro_solo_lo_propio(self):
        self.assertTrue(puede_editar_turnos_de(self.miembro, self.miembro))
        self.assertFalse(puede_editar_turnos_de(self.miembro, self.jefe))
        self.assertEqual(list(equipos_visibles(self.miembro)), [self.equipo])
        self.assertEqual(list(equipos_visibles(self.ajeno)), [])


class GoogleTests(TestCase):
    def setUp(self):
        self.ana = crear_usuario('ana')
        self.conexion = ConexionAplicacion.objects.create(usuario=self.ana, proveedor='google', cuenta='ana@x.com',
                                                          refresh_token='tok', conectada=True)

    def test_refresh_token_se_guarda_cifrado(self):
        with connection.cursor() as cursor:
            cursor.execute('SELECT refresh_token FROM agenda_conexionaplicacion WHERE id = %s', [self.conexion.pk])
            crudo = cursor.fetchone()[0]
        self.assertNotEqual(crudo, 'tok')
        self.assertEqual(ConexionAplicacion.objects.get(pk=self.conexion.pk).refresh_token, 'tok')

    def test_freebusy_convierte_a_hora_local(self):
        servicio = MagicMock()
        servicio.freebusy().query().execute.return_value = {
            'calendars': {'primary': {'busy': [{'start': '2026-10-12T14:00:00Z', 'end': '2026-10-12T15:00:00Z'}]}}}
        with patch.object(funciones_google, 'servicio_calendar', return_value=servicio):
            bloques = funciones_google.freebusy(self.conexion, datetime(2026, 10, 12, 8), datetime(2026, 10, 12, 18))
        self.assertEqual(bloques, [(datetime(2026, 10, 12, 9, 0), datetime(2026, 10, 12, 10, 0))])
        cuerpo = servicio.freebusy().query.call_args.kwargs['body']
        self.assertEqual(cuerpo['timeZone'], 'America/Guayaquil')
        self.assertTrue(cuerpo['timeMin'].endswith('-05:00'))

    def test_crear_evento_pide_meet_y_avisa(self):
        servicio = MagicMock()
        servicio.events().insert().execute.return_value = {'id': 'ev1', 'hangoutLink': 'https://meet.google.com/abc',
                                                           'htmlLink': 'https://calendar/ev1'}
        with patch.object(funciones_google, 'servicio_calendar', return_value=servicio):
            resultado = funciones_google.crear_evento(self.conexion, 'Cita', datetime(2026, 10, 12, 9),
                                                      datetime(2026, 10, 12, 9, 40), invitados=['c@x.com'],
                                                      request_id='cita-1', extra={'cita_id': 1})
        self.assertEqual(resultado, ('ev1', 'https://meet.google.com/abc', 'https://calendar/ev1'))
        llamada = servicio.events().insert.call_args.kwargs
        self.assertEqual(llamada['conferenceDataVersion'], 1)
        self.assertEqual(llamada['sendUpdates'], 'all')
        self.assertEqual(llamada['body']['conferenceData']['createRequest']['requestId'], 'cita-1')
        self.assertEqual(llamada['body']['attendees'], [{'email': 'c@x.com'}])
        self.assertEqual(llamada['body']['extendedProperties']['private']['cita_id'], '1')

    def test_token_rechazado_desconecta(self):
        from google.auth.exceptions import RefreshError
        with patch('google.oauth2.credentials.Credentials.refresh', side_effect=RefreshError('invalid_grant: bad')):
            with self.assertRaises(funciones_google.ErrorGoogle):
                funciones_google.credenciales_de(self.conexion)
        self.conexion.refresh_from_db()
        self.assertFalse(self.conexion.conectada)
        self.assertIn('volver a conectar', self.conexion.ultimo_error)

    def test_pantalla_sin_configurar_no_ofrece_conectar(self):
        self.ana.is_superuser = True
        self.ana.save()
        self.client.force_login(self.ana)
        with self.settings(GOOGLE_OAUTH_CLIENT_ID='', GOOGLE_OAUTH_CLIENT_SECRET=''):
            respuesta = self.client.get('/agenda/aplicaciones/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'todavía no está configurado')
        self.assertNotContains(respuesta, 'action=conectar_google')


class PortalTests(TestCase):
    def setUp(self):
        from .models import Cliente, Portal, Producto, TokenAcceso
        from . import funciones_portal, funciones_tokens
        self.funciones_portal, self.funciones_tokens = funciones_portal, funciones_tokens
        self.Cliente, self.TokenAcceso = Cliente, TokenAcceso
        self.ana = crear_usuario('ana')
        proyecto = Proyecto.objects.create(codigo='demo', nombre='Demo', lider=self.ana)
        self.equipo = Equipo.objects.create(proyecto=proyecto, nombre='Equipo demo', lider=self.ana)
        MiembroEquipo.objects.create(equipo=self.equipo, usuario=self.ana, rol='responsable')
        hoy = date.today()
        self.lunes = hoy + timedelta(days=(7 - hoy.weekday()) % 7 or 7)
        if (self.lunes - hoy).days < 3:
            self.lunes += timedelta(days=7)
        patron = PatronTurno.objects.create(usuario=self.ana, vigencia_desde=hoy)
        FranjaTurno.objects.create(patron=patron, dia_semana=0, hora_inicio=time(9, 0), hora_fin=time(11, 0))
        portal = Portal.objects.create(nombre='Demo', slug='demo', principal=True)
        self.producto = Producto.objects.create(portal=portal, slug='kawana', nombre='Kawana', equipo=self.equipo,
                                                duracion_min=40, antelacion_horas=1, ventana_dias=30)
        self.datos = {'nombres': 'Cliente Prueba', 'correo': 'cliente@prueba.com', 'telefono': '', 'mensaje': ''}

    def test_dias_y_espacios_del_producto(self):
        dias = self.funciones_portal.dias_con_cupo(self.producto)
        self.assertIn(self.lunes, [d['fecha'] for d in dias])
        espacios = self.funciones_portal.espacios_del_dia(self.producto, self.lunes)
        self.assertEqual([e.strftime('%H:%M') for e in espacios], ['09:00', '09:40', '10:20'])

    def test_dias_con_cupo_no_consulta_por_dia(self):
        from django.test.utils import CaptureQueriesContext
        self.funciones_portal.dias_con_cupo(self.producto, dias=7)
        with CaptureQueriesContext(connection) as semana:
            self.funciones_portal.dias_con_cupo(self.producto, dias=7)
        with CaptureQueriesContext(connection) as mes:
            dias = self.funciones_portal.dias_con_cupo(self.producto, dias=30)
        self.assertEqual(len(mes), len(semana))
        self.assertIn(self.lunes, [d['fecha'] for d in dias])

    def test_reservar_crea_cita_tokens_y_bloquea_el_horario(self):
        inicio = datetime.combine(self.lunes, time(9, 0))
        with patch.object(self.funciones_portal.funciones_avisos_cita, 'avisar_reserva'):
            cita, token = self.funciones_portal.reservar(self.producto, inicio, self.datos)
        self.assertEqual(cita.asignada_por, 'cliente')
        self.assertEqual(cita.fin, inicio + timedelta(minutes=40))
        self.assertEqual(self.TokenAcceso.objects.filter(cita=cita, tipo='cita').count(), 1)
        self.assertEqual(self.TokenAcceso.objects.filter(cliente=cita.cliente, tipo='cliente').count(), 1)
        self.assertEqual(self.funciones_tokens.validar(token, 'cita').cita_id, cita.pk)
        self.assertIsNone(self.funciones_tokens.validar(token, 'cliente'))
        self.assertNotIn(inicio, self.funciones_portal.espacios_del_dia(self.producto, self.lunes))
        with self.assertRaises(ValueError):
            self.funciones_portal.reservar(self.producto, inicio, dict(self.datos, correo='otro@prueba.com'))

    def test_paginas_publicas(self):
        from django.test import Client as Navegador
        navegador = Navegador()
        r = navegador.get('/kawana/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '¿Qué día le queda bien?')
        r = navegador.get(f'/kawana/?action=horas&fecha={self.lunes:%Y-%m-%d}')
        self.assertEqual(len(r.json()['data']), 3)
        with patch.object(self.funciones_portal.funciones_avisos_cita, 'avisar_reserva'):
            r = navegador.post('/kawana/', dict(self.datos, action='reservar',
                                                        inicio=f'{self.lunes:%Y-%m-%d}T09:40'))
        self.assertFalse(r.json()['error'], r.json())
        destino = r.json()['to']
        r = navegador.get(destino)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Su cita quedó agendada')
        r = navegador.post(destino, {'action': 'reprogramar', 'inicio': f'{self.lunes:%Y-%m-%d}T10:20'})
        self.assertFalse(r.json()['error'], r.json())
        r = navegador.post(destino, {'action': 'cancelar', 'motivo': 'Prueba'})
        self.assertFalse(r.json()['error'])
        self.assertContains(navegador.get(destino), 'Esta cita fue cancelada')
        self.assertEqual(navegador.get('/cita/no-existe/').status_code, 410)
        token_cliente = self.funciones_tokens.emitir('cliente', cliente=self.Cliente.objects.get(correo='cliente@prueba.com'))
        r = navegador.get(f'/conectar/demo/{token_cliente}/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Hola, Cliente Prueba')

    def test_pedir_llamada_entra_en_cola(self):
        from django.test import Client as Navegador
        r = Navegador().post('/kawana/', dict(self.datos, action='llamar', telefono='0999999999'))
        self.assertFalse(r.json()['error'], r.json())
        from .models import Solicitud
        self.assertEqual(Solicitud.objects.filter(estado='en_cola', origen='portal').count(), 1)

    def test_apartado_temporal_oculta_el_horario_a_otros(self):
        from django.core.cache import cache
        cache.clear()
        inicio = datetime.combine(self.lunes, time(9, 0))
        self.assertTrue(self.funciones_portal.apartar(self.producto, inicio, 'sesion-a'))
        self.assertFalse(self.funciones_portal.apartar(self.producto, inicio, 'sesion-b'))
        self.assertNotIn(inicio, self.funciones_portal.espacios_del_dia(self.producto, self.lunes, 'sesion-b'))
        self.assertIn(inicio, self.funciones_portal.espacios_del_dia(self.producto, self.lunes, 'sesion-a'))
        self.funciones_portal.liberar(self.producto, inicio, 'sesion-a')
        self.assertIn(inicio, self.funciones_portal.espacios_del_dia(self.producto, self.lunes, 'sesion-b'))

    def test_ventana_incrustable_permite_los_sitios_del_portal(self):
        from django.test import Client as Navegador
        self.producto.portal.sitios_autorizados = 'https://exducereonline.com'
        self.producto.portal.save()
        r = Navegador().get('/incrustar/demo/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('https://exducereonline.com', r['Content-Security-Policy'])
        self.assertNotIn('X-Frame-Options', r)
        r = Navegador().get('/kawana/?ventana=1')
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'pb-header')


class BusquedaTests(TestCase):
    def test_busca_sin_tildes_y_por_codigo(self):
        from .funciones_busqueda import buscar
        from .funciones_citas import codigo_cliente
        from .models import Cliente
        ana = crear_usuario('ana')
        Group.objects.get_or_create(name=ROL_ADMINISTRADOR)[0].user_set.add(ana)
        Cliente.objects.create(codigo=codigo_cliente(), nombres='José Pérez', correo='jose@prueba.com')
        r = buscar('jose perez', ana)
        self.assertEqual([c.nombres for c in r['clientes']], ['José Pérez'])
        self.assertEqual(buscar('x', ana)['total'], 0)


class BaseReservaTests(TestCase):
    """Usuario con turno los lunes 9:00-11:00 y un producto del portal para reservar."""

    def setUp(self):
        from .models import Portal, Producto
        from . import funciones_portal
        self.funciones_portal = funciones_portal
        self.ana = crear_usuario('ana')
        proyecto = Proyecto.objects.create(codigo='demo', nombre='Demo', lider=self.ana)
        self.equipo = Equipo.objects.create(proyecto=proyecto, nombre='Equipo demo', lider=self.ana)
        MiembroEquipo.objects.create(equipo=self.equipo, usuario=self.ana, rol='responsable')
        hoy = date.today()
        self.lunes = hoy + timedelta(days=(7 - hoy.weekday()) % 7 or 7)
        if (self.lunes - hoy).days < 3:
            self.lunes += timedelta(days=7)
        patron = PatronTurno.objects.create(usuario=self.ana, vigencia_desde=hoy)
        FranjaTurno.objects.create(patron=patron, dia_semana=0, hora_inicio=time(9, 0), hora_fin=time(11, 0))
        self.portal = Portal.objects.create(nombre='Demo', slug='demo', principal=True)
        self.producto = Producto.objects.create(portal=self.portal, slug='kawana', nombre='Kawana', equipo=self.equipo,
                                                duracion_min=40, antelacion_horas=1, ventana_dias=30)
        self.datos = {'nombres': 'Cliente Prueba', 'correo': 'cliente@prueba.com', 'telefono': '', 'mensaje': ''}

    def reservar(self, hora=time(9, 0)):
        with patch.object(self.funciones_portal.funciones_avisos_cita, 'avisar_reserva'):
            return self.funciones_portal.reservar(self.producto, datetime.combine(self.lunes, hora), self.datos)


class LogoProductoTests(BaseReservaTests):
    def _archivo(self, nombre, tamano=100):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(nombre, b'0' * tamano, content_type='application/octet-stream')

    def test_logo_valida_extension_y_tamano(self):
        from django.core.exceptions import ValidationError
        campo = self.producto._meta.get_field('logo')
        campo.run_validators(self._archivo('logo.png'))
        with self.assertRaises(ValidationError):
            campo.run_validators(self._archivo('logo.exe'))
        with self.assertRaises(ValidationError):
            campo.run_validators(self._archivo('logo.svg'))
        with self.assertRaises(ValidationError):
            campo.run_validators(self._archivo('grande.png', 2 * 1024 * 1024 + 10))

    def test_tarjeta_del_landing_lleva_el_logo(self):
        from .funciones_portal import productos_publicos, textos
        t = textos('es')
        self.assertIsNone(productos_publicos(self.portal, 'es', t)[0]['logo'])
        self.producto.logo = 'productos/kawana.png'
        self.producto.save()
        self.assertEqual(productos_publicos(self.portal, 'es', t)[0]['logo'], '/media/productos/kawana.png')

    def test_form_de_producto_usa_dropify(self):
        from .forms import ProductoForm
        form = ProductoForm(portal=self.portal)
        self.assertEqual(form.fields['logo'].widget.attrs['class'], 'dropify')
        self.assertIn('.png', form.fields['logo'].widget.attrs['accept'])


class AvisosProximosTests(BaseReservaTests):
    def setUp(self):
        super().setUp()
        from . import funciones_avisos_proximos
        self.avisos = funciones_avisos_proximos
        self.correo = patch.object(funciones_avisos_proximos.correos, 'enviar_ahora', return_value=True).start()
        self.push = patch('pwa.notificaciones.enviar_push_usuario', return_value=True).start()
        self.addCleanup(patch.stopall)
        self.ana.email = 'ana@prueba.com'
        self.ana.save()

    def test_cita_del_portal_avisa_solo_al_responsable_una_vez(self):
        from .models import AvisoProximo
        cita, _ = self.reservar()
        self.assertEqual(self.avisos.enviar_avisos_proximos(cita.inicio - timedelta(minutes=8)), (2, 0))
        self.assertEqual(set(AvisoProximo.objects.filter(cita=cita).values_list('usuario_id', 'canal')),
                         {(self.ana.pk, 'correo'), (self.ana.pk, 'push')})
        self.assertEqual(self.avisos.enviar_avisos_proximos(cita.inicio - timedelta(minutes=5)), (0, 0))
        self.assertEqual(self.correo.call_count, 1)
        self.assertEqual(self.push.call_count, 1)

    def test_avisa_tambien_a_quien_agendo(self):
        from .models import AvisoProximo, Cita
        cita, _ = self.reservar()
        bea = crear_usuario('bea')
        bea.email = 'bea@prueba.com'
        bea.save()
        Cita.objects.filter(pk=cita.pk).update(usuario_creacion=bea)
        self.avisos.enviar_avisos_proximos(cita.inicio - timedelta(minutes=10))
        self.assertEqual(set(AvisoProximo.objects.filter(cita=cita, canal='correo').values_list('usuario_id', flat=True)),
                         {self.ana.pk, bea.pk})

    def test_fuera_de_la_ventana_no_avisa(self):
        cita, _ = self.reservar()
        self.assertEqual(self.avisos.enviar_avisos_proximos(cita.inicio - timedelta(minutes=11)), (0, 0))
        self.assertEqual(self.avisos.enviar_avisos_proximos(cita.inicio + timedelta(minutes=1)), (0, 0))

    def test_reunion_avisa_al_organizador_y_registra_el_fallo_de_push(self):
        from .models import AvisoProximo, Reunion
        inicio = datetime.combine(self.lunes, time(10, 0))
        reunion = Reunion.objects.create(organizador=self.ana, plataforma='google', titulo='Revisión', inicio=inicio,
                                         fin=inicio + timedelta(minutes=30))
        self.push.return_value = False
        self.assertEqual(self.avisos.enviar_avisos_proximos(inicio - timedelta(minutes=3)), (1, 1))
        self.assertFalse(AvisoProximo.objects.get(reunion=reunion, canal='push').exito)
        self.assertEqual(self.avisos.enviar_avisos_proximos(inicio - timedelta(minutes=2)), (0, 0))


class IdsCifradosTests(BaseReservaTests):
    def test_cifrar_y_descifrar(self):
        from core.crypto import cifrar_id, descifrar_id
        token = cifrar_id(42)
        self.assertNotIn('42', token)
        self.assertEqual(descifrar_id(token), 42)
        self.assertNotEqual(cifrar_id(42), token)
        self.assertIsNone(descifrar_id('42'))
        self.assertIsNone(descifrar_id(token[:-4] + 'AAAA'))
        self.assertIsNone(descifrar_id(''))

    def test_mis_citas_no_expone_ids_y_solo_acepta_el_cifrado(self):
        import re
        from django.test import Client as Navegador
        from . import funciones_tokens
        cita, _ = self.reservar()
        url = f'/conectar/demo/{funciones_tokens.emitir("cliente", cliente=cita.cliente)}/'
        navegador = Navegador()
        html = navegador.get(url).content.decode()
        self.assertNotRegex(html, rf'(cita-|pt-cambio-|pt-cancelar-|name="cita" value="){cita.pk}\b')
        ref = re.search(r'name="cita" value="([^"]+)"', html).group(1)
        r = navegador.post(url, {'action': 'cancelar', 'cita': str(cita.pk), 'motivo': 'x'})
        self.assertTrue(r.json()['error'])
        r = navegador.post(url, {'action': 'cancelar', 'cita': ref, 'motivo': 'Prueba'})
        self.assertFalse(r.json()['error'], r.json())


class MiAgendaTurnosTests(BaseReservaTests):
    def setUp(self):
        super().setUp()
        self.ana.is_superuser = True
        self.ana.save()

    def test_validar_horario(self):
        from .funciones_disponibilidad import HorarioNoDisponible, validar_horario
        nueve = datetime.combine(self.lunes, time(9, 0))
        validar_horario(self.ana, nueve, nueve + timedelta(minutes=30))
        with self.assertRaisesMessage(HorarioNoDisponible, 'fuera de tus turnos') as error:
            validar_horario(self.ana, nueve + timedelta(hours=3), nueve + timedelta(hours=3, minutes=30))
        self.assertTrue(error.exception.sugerencias)
        cita, _ = self.reservar()
        with self.assertRaisesMessage(HorarioNoDisponible, 'Ya tienes algo agendado'):
            validar_horario(self.ana, nueve, nueve + timedelta(minutes=30))
        validar_horario(self.ana, nueve, nueve + timedelta(minutes=30), ignorar=[(cita.inicio, cita.fin)])
        with self.assertRaisesMessage(HorarioNoDisponible, 'ya pasó'):
            validar_horario(self.ana, datetime.now() - timedelta(hours=1), datetime.now())

    def test_horas_libres_solo_dentro_del_turno(self):
        from .funciones_disponibilidad import horas_libres
        self.reservar()
        horas = [h['texto'] for h in horas_libres(self.ana, self.lunes, 40)]
        self.assertNotIn('09:00', horas)
        self.assertTrue(horas)
        self.assertTrue(all('09:00' <= h <= '10:20' for h in horas))
        self.assertEqual(horas_libres(self.ana, self.lunes + timedelta(days=1), 40), [])

    def test_vista_rechaza_reunion_fuera_de_turno_y_sugiere(self):
        self.client.force_login(self.ana)
        r = self.client.post('/agenda/mi-agenda/', {'action': 'reunion', 'plataforma': 'google', 'titulo': 'Fuera',
                                                     'inicio': f'{self.lunes:%Y-%m-%d}T15:00', 'duracion': 30})
        res = r.json()[0]
        self.assertTrue(res['error'])
        self.assertIn('inicio', res['form'][0])
        self.assertTrue(res['sugerencias'])
        r = self.client.get('/agenda/mi-agenda/', {'action': 'horas_libres', 'fecha': self.lunes.isoformat(), 'duracion': 30})
        self.assertEqual(r.json()['horas'][0]['valor'], f'{self.lunes:%Y-%m-%d}T09:00')

    def test_form_de_cita_atado_a_turnos(self):
        self.client.force_login(self.ana)
        r = self.client.get('/agenda/mi-agenda/', {'action': 'agendar', 'inicio': f'{self.lunes:%Y-%m-%d}T09:00',
                                                   'duracion': 40})
        html = r.json()['data']
        self.assertIn('type="date"', html)
        self.assertIn(f'value="{self.lunes:%Y-%m-%d}T09:00" selected', html)
        self.assertIn('cal-sugerencias', html)


class OffcanvasAgendaTests(BaseReservaTests):
    def test_offcanvas_lista_hoy_y_proximas(self):
        self.ana.is_superuser = True
        self.ana.save()
        cita, _ = self.reservar()
        self.client.force_login(self.ana)
        r = self.client.get('/agenda/mi-dia/', {'action': 'offcanvas'})
        self.assertTrue(r.json()['result'])
        self.assertIn('Próximas reuniones', r.json()['data'])
        self.assertIn(cita.titulo, r.json()['data'])
        self.assertNotContains(self.client.get('/panel/'), 'mi-agenda-offcanvas')
        from seguridad.models import Modulo
        Modulo.objects.create(url='/agenda/mi-dia/', nombre='Mi día')
        self.assertContains(self.client.get('/panel/'), 'mi-agenda-offcanvas')
