-- Blog Platform MVP Schema v0.1
-- Postgres + pgvector
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ---------- ENUMS ----------
DO $$ BEGIN
  CREATE TYPE content_state AS ENUM (
    'INGESTED','CLASSIFIED','SELECTED','RESEARCHED','DRAFTED','VALIDATED',
    'PENDING_APPROVAL','READY_TO_PUBLISH','PUBLISHED','DEFERRED','RETIRED'
  );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE risk_tier AS ENUM ('TIER_1','TIER_2','TIER_3');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
  CREATE TYPE review_action_type AS ENUM ('APPROVE','REJECT','REQUEST_CHANGES','OVERRIDE_TIER','REFRESH','RETIRE');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- ---------- TENANCY ----------
CREATE TABLE IF NOT EXISTS tenants (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name text NOT NULL,
  slug text UNIQUE NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ---------- USERS / RBAC ----------
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  email text UNIQUE NOT NULL,
  full_name text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS roles (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name text UNIQUE NOT NULL  -- Admin, Editor, Auditor
);

CREATE TABLE IF NOT EXISTS user_roles (
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  role_id uuid NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
  PRIMARY KEY (user_id, tenant_id, role_id)
);

-- ---------- SOURCES ----------
CREATE TABLE IF NOT EXISTS sources (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name text NOT NULL,
  type text NOT NULL, -- rss, api, manual
  url text,
  is_enabled boolean NOT NULL DEFAULT true,
  reputation_score int NOT NULL DEFAULT 50,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ---------- INTAKE ----------
CREATE TABLE IF NOT EXISTS intake_items (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  source_id uuid REFERENCES sources(id) ON DELETE SET NULL,
  source_url text,
  title text,
  raw_text text,
  raw_hash text NOT NULL,
  published_at timestamptz,
  ingested_at timestamptz NOT NULL DEFAULT now(),
  integrity_flags jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_intake_tenant_ingested ON intake_items(tenant_id, ingested_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_intake_tenant_hash ON intake_items(tenant_id, raw_hash);

-- ---------- CONTENT ITEM ----------
CREATE TABLE IF NOT EXISTS content_items (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  intake_id uuid REFERENCES intake_items(id) ON DELETE SET NULL,
  state content_state NOT NULL DEFAULT 'INGESTED',
  domain_primary text,
  domain_secondary text[],
  risk risk_tier NOT NULL DEFAULT 'TIER_1',
  decision_confidence numeric(4,3),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_content_tenant_state ON content_items(tenant_id, state);

-- ---------- PROMPTS & POLICIES (VERSIONED) ----------
CREATE TABLE IF NOT EXISTS prompt_versions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  agent_name text NOT NULL,
  version text NOT NULL,
  prompt text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, agent_name, version)
);

CREATE TABLE IF NOT EXISTS policy_versions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  version text NOT NULL,
  policy jsonb NOT NULL,
  is_active boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, version)
);

-- ---------- DRAFTS & PUBLICATIONS ----------
CREATE TABLE IF NOT EXISTS draft_versions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  content_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
  version int NOT NULL DEFAULT 1,
  title text,
  body_md text NOT NULL,
  citations jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, content_id, version)
);

CREATE TABLE IF NOT EXISTS publications (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  content_id uuid NOT NULL REFERENCES content_items(id) ON DELETE RESTRICT,
  draft_id uuid NOT NULL REFERENCES draft_versions(id) ON DELETE RESTRICT,
  slug text NOT NULL,
  is_live boolean NOT NULL DEFAULT false,
  published_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(tenant_id, slug)
);

-- ---------- PROVENANCE (APPEND-ONLY) ----------
CREATE TABLE IF NOT EXISTS provenance_events (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  content_id uuid REFERENCES content_items(id) ON DELETE SET NULL,
  intake_id uuid REFERENCES intake_items(id) ON DELETE SET NULL,
  agent_name text NOT NULL,
  prompt_version_id uuid REFERENCES prompt_versions(id) ON DELETE SET NULL,
  policy_version_id uuid REFERENCES policy_versions(id) ON DELETE SET NULL,
  model_name text,
  input_hash text,
  output_hash text,
  status text NOT NULL, -- started, completed, failed
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prov_tenant_content_time ON provenance_events(tenant_id, content_id, created_at DESC);

-- ---------- REVIEW ACTIONS ----------
CREATE TABLE IF NOT EXISTS review_actions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  content_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  action review_action_type NOT NULL,
  comment text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ---------- UPDATED_AT TRIGGER ----------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_content_updated_at ON content_items;
CREATE TRIGGER trg_content_updated_at
BEFORE UPDATE ON content_items
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();
