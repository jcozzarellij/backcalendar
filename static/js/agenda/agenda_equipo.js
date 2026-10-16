(function () {
    const equipo = document.getElementById('equipo');
    document.querySelectorAll('.ae-agendar').forEach(function (boton) {
        boton.addEventListener('click', function () {
            formModal(0, 'Agendar a las ' + boton.dataset.inicio.slice(11), 'agendar', {
                inicio: boton.dataset.inicio,
                equipo: equipo ? equipo.value : ''
            });
        });
    });
})();
