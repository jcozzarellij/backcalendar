function leerAlerta(id) {
    const datos = new FormData();
    datos.append('action', 'leer');
    datos.append('id', id);
    datos.append('csrfmiddlewaretoken', csrfAgenda());
    if (navigator.sendBeacon) {
        navigator.sendBeacon('/agenda/alertas/', datos);
    } else {
        fetch('/agenda/alertas/', {method: 'POST', body: datos, credentials: 'same-origin', keepalive: true});
    }
}
