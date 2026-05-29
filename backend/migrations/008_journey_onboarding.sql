-- ============================================================
-- Migration 008 — Parcours d'affaire guidé + onboarding
-- ============================================================

-- ------------------------------------------------------------
-- 1. Parcours d'affaire sur les projets
-- ------------------------------------------------------------

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS current_phase TEXT DEFAULT 'initiation',
    ADD COLUMN IF NOT EXISTS commune TEXT,
    ADD COLUMN IF NOT EXISTS canton TEXT DEFAULT 'VD',
    ADD COLUMN IF NOT EXISTS sre_m2 NUMERIC,
    ADD COLUMN IF NOT EXISTS nb_logements INTEGER,
    ADD COLUMN IF NOT EXISTS affectation TEXT,
    ADD COLUMN IF NOT EXISTS labels JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS phase_sia_demarrage TEXT;

COMMENT ON COLUMN projects.current_phase IS
    'Phase courante du parcours d''affaire (clé de project_journey).';
COMMENT ON COLUMN projects.labels IS
    'Labels visés : Minergie-P, CVSE, CECB, etc.';


-- ------------------------------------------------------------
-- 2. Modularité du parcours par organisation
-- ------------------------------------------------------------

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS disabled_journey_phases JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS onboarding_step INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN organizations.disabled_journey_phases IS
    'Phases du parcours désactivées (ex: bureau sans suivi de chantier).';
COMMENT ON COLUMN organizations.onboarding_completed IS
    'TRUE quand l''organisation a terminé le wizard d''onboarding.';
COMMENT ON COLUMN organizations.onboarding_step IS
    'Étape courante de l''onboarding (0 = pas commencé).';


-- ------------------------------------------------------------
-- 3. Notifications proactives
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    type TEXT NOT NULL CHECK (type IN (
        'task_completed',        -- une tâche est terminée
        'pending_validation',    -- documents en attente de validation
        'deadline_approaching',  -- échéance AEAI/permis proche
        'deadline_overdue',      -- échéance dépassée
        'quota_warning',         -- quota tokens proche de la limite
        'phase_suggestion'       -- suggestion de prochaine action
    )),
    severity TEXT NOT NULL DEFAULT 'info'
        CHECK (severity IN ('info', 'warning', 'urgent')),

    title TEXT NOT NULL,
    body TEXT,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    action_url TEXT,

    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_org_unread
    ON notifications(organization_id, created_at DESC)
    WHERE read_at IS NULL;

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY notifications_select ON notifications
    FOR SELECT USING (organization_id = current_organization_id());


-- ------------------------------------------------------------
-- 4. Échéances projet (pour les notifications de délai)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS project_deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    label TEXT NOT NULL,           -- "Dépôt AEAI", "Permis de construire", etc.
    phase_key TEXT,                -- phase du parcours associée
    due_date DATE NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deadlines_org_due
    ON project_deadlines(organization_id, due_date)
    WHERE completed = FALSE;

ALTER TABLE project_deadlines ENABLE ROW LEVEL SECURITY;

CREATE POLICY deadlines_select ON project_deadlines
    FOR SELECT USING (organization_id = current_organization_id());
