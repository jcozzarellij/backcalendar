from django.contrib.auth.decorators import login_required

from .view_index_adm import index_adm


@login_required
def index(request):
    return index_adm(request)
