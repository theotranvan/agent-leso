-- ============================================================
-- BET Agent - Migration Supabase complète
-- À exécuter dans l'ordre dans l'éditeur SQL Supabase
-- ============================================================

-- Extensions nécessaires
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_cron";

-- ============================================================
-- TABLES
-- ============================================================

-- Organizations (un BET = une organization)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    siret TEXT,
    email TEXT NOT NULL UNIQUE,
    plan TEXT NOT NULL DEFAULT 'starter' CHECK (plan IN ('starter', 'pro', 'enterprise')),
    tasks_used_this_month INTEGER DEFAULT 0,
    tasks_limit INTEGER DEFAULT 500,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_organizations_email ON organizations(email);
CREATE INDEX IF NOT EXISTS idx_organizations_stripe_customer ON organizations(stripe_customer_id);

-- Users (liés à auth.users Supabase)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member', 'viewer')),
    full_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id);

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type_ouvrage TEXT,
    address TEXT,
    lots TEXT[] DEFAULT '{}',
    normes_applicables TEXT[] DEFAULT '{}',
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_organization ON projects(organization_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(organization_id, status);

-- Documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'ifc', 'bcf', 'xlsx', 'image')),
    storage_path TEXT NOT NULL,
    extracted_text TEXT,
    page_count INTEGER,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_organization ON documents(organization_id);
CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_processed ON documents(organization_id, processed);

-- Embeddings vectoriels
CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index vectoriel IVFFlat (cosine) - 100 listes conseillé jusqu'à ~1M vecteurs
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON document_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Index pour filtres multi-tenant (essentiels à la perf)
CREATE INDEX IF NOT EXISTS idx_embeddings_org_project ON document_embeddings(organization_id, project_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_document ON document_embeddings(document_id);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    model_used TEXT,
    input_params JSONB DEFAULT '{}',
    result_url TEXT,
    result_preview TEXT,
    tokens_used INTEGER DEFAULT 0,
    cost_euros NUMERIC(10, 4) DEFAULT 0,
    error_message TEXT,
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tasks_organization ON tasks(organization_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(organization_id, created_at DESC);

-- Regulatory alerts
CREATE TABLE IF NOT EXISTS regulatory_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    content_summary TEXT,
    affected_domains TEXT[] DEFAULT '{}',
    published_at TIMESTAMPTZ,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_published ON regulatory_alerts(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_processed ON regulatory_alerts(processed, published_at DESC);

-- Audit logs (immuable)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID,
    user_id UUID,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id UUID,
    ip_address INET,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_organization ON audit_logs(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id, created_at DESC);

-- Empêche UPDATE/DELETE sur audit_logs (immuabilité)
REVOKE UPDATE, DELETE ON audit_logs FROM authenticated, anon;

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Fonction utilitaire : retourne organization_id courant
CREATE OR REPLACE FUNCTION current_organization_id() RETURNS UUID
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
    SELECT organization_id FROM users WHERE id = auth.uid();
$$;

-- Policies
DROP POLICY IF EXISTS "org_own" ON organizations;
CREATE POLICY "org_own" ON organizations
    FOR ALL USING (id = current_organization_id());

DROP POLICY IF EXISTS "users_own_org" ON users;
CREATE POLICY "users_own_org" ON users
    FOR ALL USING (organization_id = current_organization_id() OR id = auth.uid());

DROP POLICY IF EXISTS "projects_own_org" ON projects;
CREATE POLICY "projects_own_org" ON projects
    FOR ALL USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "documents_own_org" ON documents;
CREATE POLICY "documents_own_org" ON documents
    FOR ALL USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "embeddings_own_org" ON document_embeddings;
CREATE POLICY "embeddings_own_org" ON document_embeddings
    FOR ALL USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "tasks_own_org" ON tasks;
CREATE POLICY "tasks_own_org" ON tasks
    FOR ALL USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "audit_own_org" ON audit_logs;
CREATE POLICY "audit_own_org" ON audit_logs
    FOR SELECT USING (organization_id = current_organization_id());

-- ============================================================
-- FONCTIONS RPC
-- ============================================================

-- Recherche sémantique multi-tenant
CREATE OR REPLACE FUNCTION match_embeddings(
    query_embedding vector(1536),
    match_organization_id UUID,
    match_project_id UUID DEFAULT NULL,
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 8
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    chunk_index INT,
    chunk_text TEXT,
    similarity FLOAT,
    metadata JSONB
)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public AS $$
BEGIN
    RETURN QUERY
    SELECT
        de.id,
        de.document_id,
        de.chunk_index,
        de.chunk_text,
        1 - (de.embedding <=> query_embedding) AS similarity,
        de.metadata
    FROM document_embeddings de
    WHERE de.organization_id = match_organization_id
        AND (match_project_id IS NULL OR de.project_id = match_project_id)
        AND 1 - (de.embedding <=> query_embedding) > match_threshold
    ORDER BY de.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Reset mensuel des quotas
CREATE OR REPLACE FUNCTION reset_monthly_quotas() RETURNS VOID
LANGUAGE sql SECURITY DEFINER AS $$
    UPDATE organizations SET tasks_used_this_month = 0;
$$;

-- Update trigger pour projects.updated_at
CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trigger_projects_updated_at ON projects;
CREATE TRIGGER trigger_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- ============================================================
-- STORAGE BUCKET PRIVÉ
-- ============================================================

-- Créer le bucket via le dashboard Supabase OU via API :
-- INSERT INTO storage.buckets (id, name, public) VALUES ('bet-documents', 'bet-documents', false)
-- ON CONFLICT DO NOTHING;

-- RLS policy sur le bucket : uniquement accès via service_role côté backend
-- Les utilisateurs ne téléchargent que via URLs signées générées par le backend

-- ============================================================
-- FIN DE LA MIGRATION
-- ============================================================
