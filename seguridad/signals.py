def create_authgroup(sender, instance, created, **kwargs):
    from seguridad.models import GroupModulo
    # Sin `status`: es OneToOne con el grupo, así que filtrarlo no vería una fila dada de
    # baja y el create chocaría contra la unicidad.
    if not GroupModulo.objects.filter(group_id=instance.pk).exists():
        GroupModulo.objects.create(group_id=instance.pk)