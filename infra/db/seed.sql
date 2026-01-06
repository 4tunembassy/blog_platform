-- Idempotent seed for local dev
INSERT INTO tenants (id, name, slug, created_at)
VALUES ('00000000-0000-0000-0000-000000000001', 'Default Tenant', 'default', now())
ON CONFLICT (slug) DO NOTHING;
