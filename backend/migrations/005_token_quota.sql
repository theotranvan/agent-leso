-- ============================================================
-- BET Agent V5 - Système de quotas tokens + credit packs
-- À exécuter APRÈS 004_v4_agents.sql
--
-- Ce qui est ajouté :
--   * Table token_usage : log de chaque appel LLM pour facturation + analytics
--   * Table credit_packs : historique des packs achetés (5M tokens = 200 CHF)
--   * Colonnes quota sur organizations : tokens_limit, tokens_used_current,
--     tokens_pack_remaining, last_quota_alert_at
--   * VIEW token_usage_monthly : agrégation mensuelle par organisation
--   * Fonction RLS : consumption_for_org_current_month()
-- ============================================================

-- ============================================================
-- 1. TABLE token_usage
-- ============================================================

CREATE TABLE IF NOT EXISTS token_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,

    -- Type de tâche (conservé même si la task est supprimée)
    task_type TEXT,

    -- Modèle utilisé
    model TEXT NOT NULL,  -- claude-opus-4-6 | claude-sonnet-4-6 | claude-haiku-4-5-xxx

    -- Compteurs tokens
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    tokens_total INTEGER GENERATED ALWAYS AS (tokens_in + tokens_out) STORED,

    -- Coût calculé en CHF à l'instant de l'appel (pour qu'un changement
    -- de tarif Anthropic ne change pas l'historique facturé)
    cost_chf NUMERIC(10, 4) NOT NULL DEFAULT 0,

    -- Contexte additionnel
    fallback_used BOOLEAN NOT NULL DEFAULT FALSE,
    is_regeneration BOOLEAN NOT NULL DEFAULT FALSE,
    regeneration_reason TEXT,              -- motif si régénération (voir v5 régénération)
    regeneration_sections TEXT[],          -- sections ciblées
    regeneration_attempt INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_token_usage_org_created ON token_usage(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_token_usage_task ON token_usage(task_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_org_month ON token_usage(organization_id, date_trunc('month', created_at));

ALTER TABLE token_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY token_usage_select ON token_usage
    FOR SELECT
    USING (organization_id = current_organization_id());

-- Seul le backend (service_role) peut INSERT
CREATE POLICY token_usage_insert_service ON token_usage
    FOR INSERT
    WITH CHECK (false);  -- aucun client, pas même authenticated


-- ============================================================
-- 2. TABLE credit_packs — historique achats additionnels
-- ============================================================

CREATE TABLE IF NOT EXISTS credit_packs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Infos Stripe
    stripe_session_id TEXT UNIQUE,         -- idempotence webhook
    stripe_payment_intent_id TEXT,

    -- Pack
    tokens_granted INTEGER NOT NULL,       -- 5_000_000 par défaut
    price_chf_paid NUMERIC(10, 2) NOT NULL,

    -- Consommation du pack (ce compteur décrémente au fil de l'utilisation)
    tokens_remaining INTEGER NOT NULL,
    fully_consumed_at TIMESTAMPTZ,

    purchased_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credit_packs_org ON credit_packs(organization_id, purchased_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_packs_remaining ON credit_packs(organization_id)
    WHERE tokens_remaining > 0;

ALTER TABLE credit_packs ENABLE ROW LEVEL SECURITY;

CREATE POLICY credit_packs_select ON credit_packs
    FOR SELECT
    USING (organization_id = current_organization_id());


-- ============================================================
-- 3. Extension de organizations avec compteurs quota
-- ============================================================

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS tokens_limit_monthly BIGINT NOT NULL DEFAULT 8000000,
    ADD COLUMN IF NOT EXISTS tokens_used_current_month BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tokens_pack_remaining BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_quota_alert_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_quota_alert_pct INTEGER,
    ADD COLUMN IF NOT EXISTS current_month_started_at TIMESTAMPTZ NOT NULL DEFAULT date_trunc('month', NOW());

COMMENT ON COLUMN organizations.tokens_limit_monthly IS
    'Quota mensuel en tokens (plan pilot=8M, pro=20M, scale=60M)';
COMMENT ON COLUMN organizations.tokens_pack_remaining IS
    'Tokens additionnels achetés via credit_packs, non consommés. Utilisés APRÈS le quota mensuel.';
COMMENT ON COLUMN organizations.last_quota_alert_at IS
    'Dernière alerte Slack envoyée (à 80% ou 100%). Évite le spam.';


-- ============================================================
-- 4. VIEW agrégée par mois
-- ============================================================

CREATE OR REPLACE VIEW token_usage_monthly AS
SELECT
    organization_id,
    date_trunc('month', created_at) AS month,
    COUNT(*) AS call_count,
    COUNT(*) FILTER (WHERE is_regeneration) AS regeneration_count,
    SUM(tokens_in) AS tokens_in_total,
    SUM(tokens_out) AS tokens_out_total,
    SUM(tokens_total) AS tokens_total,
    SUM(cost_chf) AS cost_chf_total,
    SUM(tokens_total) FILTER (WHERE model LIKE 'claude-opus-%') AS tokens_opus,
    SUM(tokens_total) FILTER (WHERE model LIKE 'claude-sonnet-%') AS tokens_sonnet,
    SUM(tokens_total) FILTER (WHERE model LIKE 'claude-haiku-%') AS tokens_haiku
FROM token_usage
GROUP BY organization_id, date_trunc('month', created_at);


-- ============================================================
-- 5. Fonction de reset mensuel (à appeler par cron le 1er du mois)
-- ============================================================

CREATE OR REPLACE FUNCTION reset_monthly_quotas()
RETURNS INTEGER AS $$
DECLARE
    affected INTEGER;
BEGIN
    UPDATE organizations
    SET
        tokens_used_current_month = 0,
        last_quota_alert_at = NULL,
        last_quota_alert_pct = NULL,
        current_month_started_at = date_trunc('month', NOW())
    WHERE current_month_started_at < date_trunc('month', NOW());

    GET DIAGNOSTICS affected = ROW_COUNT;
    RETURN affected;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ============================================================
-- 6. Régénérations — extension de la table tasks
-- ============================================================

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS regeneration_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_regenerated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS regeneration_history JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN tasks.regeneration_count IS
    'Nombre de régénérations effectuées. Max 5 (constante côté app).';
COMMENT ON COLUMN tasks.regeneration_history IS
    'Array: [{at, reasons, sections, motif_text, model_used, tokens, cost_chf}]';
