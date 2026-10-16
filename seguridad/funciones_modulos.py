def urls_pendientes_por_grupo(existentes_urls):
    """URLs del diccionario del sistema (backcalendar.urls.urls_sistema) que todavía NO
    están registradas como Modulo, agrupadas por su app/sección — alimenta la vista previa
    del modal de extracción y la validación del POST de confirmación."""
    # Import local: backcalendar.urls importa las vistas que usan esta función (import circular).
    from backcalendar.urls import urls_sistema
    grupos = []
    for u in urls_sistema:
        if not u.get('sub_urls'):
            continue
        pendientes = {}
        for su in u['sub_urls']:
            mod_url = '/{}{}'.format(u['url'], su['url'])
            if mod_url in existentes_urls:
                continue
            nombre_grupo = su.get('grupo') or u.get('nombre') or u['url']
            pendientes.setdefault(nombre_grupo, []).append({'nombre': su['nombre'], 'url': mod_url})
        for nombre_grupo, urls in pendientes.items():
            grupos.append({
                'nombre': nombre_grupo,
                'base': '/{}'.format(u['url']),
                'urls': urls,
            })
    return grupos
