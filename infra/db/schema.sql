-- Minimal schema placeholder.
-- We will expand this to full SRS v1.1 schema (tenancy, RBAC, provenance, drafts, publications).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
