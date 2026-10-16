BEGIN;

DO $$
DECLARE
    t record;
BEGIN
    FOR t IN
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
          AND (tablename LIKE 'agents\_cne\_%' OR tablename LIKE 'agents\_ai\_%'
               OR tablename LIKE 'crm\_%' OR tablename LIKE 'monitoreo\_%'
               OR tablename LIKE 'langgraph%' OR tablename LIKE 'checkpoint%')
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE', t.tablename);
    END LOOP;
END $$;

DELETE FROM auth_group_permissions
WHERE permission_id IN (
    SELECT p.id FROM auth_permission p
    JOIN django_content_type c ON c.id = p.content_type_id
    WHERE c.app_label IN ('agents_cne', 'agents_ai', 'crm', 'monitoreo')
);
DELETE FROM autenticacion_usuario_user_permissions
WHERE permission_id IN (
    SELECT p.id FROM auth_permission p
    JOIN django_content_type c ON c.id = p.content_type_id
    WHERE c.app_label IN ('agents_cne', 'agents_ai', 'crm', 'monitoreo')
);
DELETE FROM auth_permission
WHERE content_type_id IN (
    SELECT id FROM django_content_type WHERE app_label IN ('agents_cne', 'agents_ai', 'crm', 'monitoreo')
);
DELETE FROM django_admin_log
WHERE content_type_id IN (
    SELECT id FROM django_content_type WHERE app_label IN ('agents_cne', 'agents_ai', 'crm', 'monitoreo')
);
DELETE FROM django_content_type WHERE app_label IN ('agents_cne', 'agents_ai', 'crm', 'monitoreo');
DELETE FROM django_migrations WHERE app IN ('agents_cne', 'agents_ai', 'crm', 'monitoreo', 'django_celery_beat', 'django_celery_results');

UPDATE seguridad_modulo SET status = FALSE
WHERE url LIKE '/agentes-cne/%' OR url LIKE '/evaluacion-cne/%' OR url LIKE '/building/%'
   OR url LIKE '/seguridad/documentacion/%';

DELETE FROM seguridad_parametrosistema WHERE grupo NOT IN ('general', 'urls');

DELETE FROM seguridad_tareacron WHERE clave NOT IN ('purgar_historicos', 'backup_bd', 'rotar_logs');

COMMIT;

SELECT app, name FROM django_migrations
WHERE app IN ('autenticacion', 'seguridad', 'area_geografica')
ORDER BY app, id;
