from django.urls import path

from .views import icono, manifest, offline, service_worker, push_subscription_status


urlpatterns = [
    path('manifest.json', manifest, name='pwa_manifest'),
    path('pwa/icono/<int:tamano>.png', icono, name='pwa_icono'),
    path('pwa/icono/<int:tamano>-maskable.png', icono, {'maskable': True}, name='pwa_icono_maskable'),
    path('serviceworker.js', service_worker, name='pwa_service_worker'),
    path('offline/', offline, name='pwa_offline'),
    path('pwa/push-estado/', push_subscription_status, name='pwa_push_estado'),
]
