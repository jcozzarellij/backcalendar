from django.contrib import messages
from django.shortcuts import redirect, render

from seguridad.models import Modulo


def redirectToUrlView(request, pk):
    mod = Modulo.objects.filter(pk=pk).first()
    if mod:
        return redirect(mod.url)
    messages.error(request, "Url no está disponible")
    return render(request, '404.html')