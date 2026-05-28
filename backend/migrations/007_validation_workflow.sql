-- ============================================================
-- Migration 007 — Workflow de validation assistée
-- ============================================================
-- Leviers de réduction du goulot de validation ingénieur :
--   Levier 1 : score de confiance auto-calculé sur chaque tâche
--   Levier 2 : alertes ciblées (stockées dans confidence_alerts)
--   Levier 3 : approbation 1-clic (review_status + colonnes d'approbation)
--   Levier 4 : délégation junior (seuil + rôle validateur)
-- ============================================================


-- ============================================================
-- 1. Colonnes de confiance et de revue sur les tâches
-- ============================================================

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS confidence_score INTEGER,
    ADD COLUMN IF NOT EXISTS confidence_level TEXT
        CHECK (confidence_level IN ('high', 'medium', 'low')),
    ADD COLUMN IF NOT EXISTS confidence_alerts JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS confidence_detail JSONB,

    -- Workflow de revue
    ADD COLUMN IF NOT EXISTS review_status TEXT
        DEFAULT 'pending_review'
        CHECK (review_status IN (
            'pending_review',     -- en attente de relecture
            'ready_to_approve',   -- confiance haute → relecture rapide
            'needs_revision',     -- confiance faible → révision nécessaire
            'approved',           -- approuvé par un valideur
            'rejected'            -- rejeté, à régénérer
        )),
    ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES users(id),
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS approval_note TEXT,
    ADD COLUMN IF NOT EXISTS approval_channel TEXT
        CHECK (approval_channel IN ('web', 'email', 'mobile', 'auto_delegated'));

COMMENT ON COLUMN tasks.confidence_score IS
    'Score de confiance auto-calculé 0-100 (Levier 1). N''engage pas la responsabilité.';
COMMENT ON COLUMN tasks.confidence_alerts IS
    'Liste des points à vérifier signalés par l''agent (Levier 2).';
COMMENT ON COLUMN tasks.review_status IS
    'État du workflow de validation (Levier 3).';
COMMENT ON COLUMN tasks.approval_channel IS
    'Canal d''approbation : web, email, mobile, ou auto_delegated (Levier 4).';

CREATE INDEX IF NOT EXISTS idx_tasks_review_status
    ON tasks(organization_id, review_status)
    WHERE review_status IN ('pending_review', 'ready_to_approve', 'needs_revision');


-- ============================================================
-- 2. Token d'approbation pour les liens email/mobile (Levier 3)
-- ============================================================
-- Permet à l'ingénieur d'approuver depuis un email sans se connecter.
-- Token à usage unique, expirant, lié à une tâche précise.

CREATE TABLE IF NOT EXISTS approval_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    token_hash TEXT NOT NULL UNIQUE,    -- hash du token (jamais le token en clair)
    action TEXT NOT NULL DEFAULT 'approve'
        CHECK (action IN ('approve', 'reject')),

    created_for_user UUID REFERENCES users(id),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,                -- NULL = pas encore utilisé

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_approval_tokens_hash
    ON approval_tokens(token_hash) WHERE used_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_approval_tokens_task
    ON approval_tokens(task_id);

ALTER TABLE approval_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY approval_tokens_select ON approval_tokens
    FOR SELECT
    USING (organization_id = current_organization_id());


-- ============================================================
-- 3. Réglages de délégation par organisation (Levier 4)
-- ============================================================
-- Permet de définir un seuil au-dessus duquel un junior peut valider,
-- et quels types de tâches restent réservés au responsable.

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS delegation_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS delegation_min_confidence INTEGER NOT NULL DEFAULT 85,
    ADD COLUMN IF NOT EXISTS delegation_reserved_tasks JSONB DEFAULT
        '["note_calcul_sia_260_267", "justificatif_sia_380_1", "dossier_mise_enquete"]'::jsonb,
    ADD COLUMN IF NOT EXISTS auto_approve_high_confidence BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN organizations.delegation_enabled IS
    'Si TRUE, un utilisateur rôle validateur peut approuver les tâches éligibles (Levier 4).';
COMMENT ON COLUMN organizations.delegation_min_confidence IS
    'Score minimum pour qu''un junior puisse valider sans le responsable.';
COMMENT ON COLUMN organizations.delegation_reserved_tasks IS
    'Types de tâches engageant la responsabilité pro, réservés au responsable.';
COMMENT ON COLUMN organizations.auto_approve_high_confidence IS
    'Si TRUE, les tâches non réservées et de confiance haute passent directement approved.';


-- ============================================================
-- 4. Rôle validateur sur les utilisateurs (Levier 4)
-- ============================================================
-- On étend le système de rôles existant. Un 'validator' peut approuver
-- les tâches éligibles ; un 'engineer_responsible' peut tout approuver.

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS can_validate BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_engineer_responsible BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN users.can_validate IS
    'Peut valider les tâches éligibles à la délégation (junior validateur).';
COMMENT ON COLUMN users.is_engineer_responsible IS
    'Ingénieur responsable : peut approuver toutes les tâches, y compris réservées.';


-- ============================================================
-- 5. Vue agrégée : file de validation par organisation
-- ============================================================

CREATE OR REPLACE VIEW review_queue AS
SELECT
    t.id AS task_id,
    t.organization_id,
    t.task_type,
    t.review_status,
    t.confidence_score,
    t.confidence_level,
    t.confidence_alerts,
    t.result_preview,
    t.created_at,
    t.completed_at,
    p.name AS project_name,
    CASE
        WHEN t.confidence_level = 'high' THEN 1
        WHEN t.confidence_level = 'medium' THEN 2
        ELSE 3
    END AS review_priority
FROM tasks t
LEFT JOIN projects p ON p.id = t.project_id
WHERE t.status = 'completed'
  AND t.review_status IN ('pending_review', 'ready_to_approve', 'needs_revision');
