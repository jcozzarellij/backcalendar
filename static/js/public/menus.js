document.addEventListener('click', function (evento) {
    document.querySelectorAll('.pb-menu[open]').forEach(function (menu) {
        if (!menu.contains(evento.target)) {
            menu.removeAttribute('open');
        }
    });
});

document.addEventListener('keydown', function (evento) {
    if (evento.key !== 'Escape') {
        return;
    }
    document.querySelectorAll('.pb-menu[open]').forEach(function (menu) {
        menu.removeAttribute('open');
        menu.querySelector('summary').focus();
    });
});
