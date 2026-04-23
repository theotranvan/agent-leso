-- ============================================================
-- BET Agent V4 - Nouveaux agents haute valeur ajoutée
-- À exécuter APRÈS 003_v3_connectors.sql
--
-- Tables ajoutées :
--   * dossiers_enquete        : suivi des dossiers APA/APC avec couverture pièces
--   * observations_autorite   : courriers autorité reçus + lettres de réponse
--   * metres_ifc              : historique des métrés extraits depuis IFC
--   * simulations_rapides     : simulations énergétiques avant-projet
-- ============================================================

-- ============================================================
-- 1. DOSSIERS MISE EN ENQUÊTE (APA / APC)
-- ============================================================

CREATE TABLE IF NOT EXISTS dossiers_enquete (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    canton TEXT NOT NULL,
    procedure_type TEXT NOT NULL,           -- 'APA', 'APC', 'permis_construire', 'mise_enquete'
    project_data JSONB NOT NULL DEFAULT '{}',

    -- Pièces à fournir et leur statut
    pieces_attendues JSONB NOT NULL DEFAULT '[]',   -- [{code, nom, format, responsable}]
    pieces_presentes TEXT[] DEFAULT '{}',           -- codes A01, A02... présents
    pieces_manquantes TEXT[] DEFAULT '{}',
    coverage_pct NUMERIC(5,2),

    -- Livrables générés
    memoire_pdf_path TEXT,
    checklist_consolidee_md TEXT,
    warnings JSONB DEFAULT '[]',

    -- Statut
    status TEXT DEFAULT 'draft'
        CHECK (status IN ('draft', 'review', 'complete', 'submitted', 'accepted', 'observations_received', 'closed')),
    submitted_at TIMESTAMPTZ,
    authority_reference TEXT,                -- Référence attribuée par l'autorité au dépôt

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dossiers_enquete_org ON dossiers_enquete(organization_id);
CREATE INDEX IF NOT EXISTS idx_dossiers_enquete_project ON dossiers_enquete(project_id);
CREATE INDEX IF NOT EXISTS idx_dossiers_enquete_status ON dossiers_enquete(status);
CREATE INDEX IF NOT EXISTS idx_dossiers_enquete_canton ON dossiers_enquete(canton);

-- ============================================================
-- 2. OBSERVATIONS AUTORITÉ (courrier reçu + réponse générée)
-- ============================================================

CREATE TABLE IF NOT EXISTS observations_autorite (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    dossier_enquete_id UUID REFERENCES dossiers_enquete(id) ON DELETE SET NULL,

    authority TEXT NOT NULL,                 -- 'DALE', 'DGT', 'SAT', 'ECA', ...
    their_reference TEXT,
    our_reference TEXT,
    received_at DATE,
    deadline_at DATE,                        -- Délai de réponse imposé par autorité

    -- Document source
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,

    -- Analyse
    observations_parsed JSONB DEFAULT '[]',  -- [{num, title, text, theme}]
    nb_observations INTEGER,
    themes_detected TEXT[] DEFAULT '{}',

    -- Réponse
    reponse_pdf_path TEXT,
    reponse_md TEXT,
    sent_at TIMESTAMPTZ,

    status TEXT DEFAULT 'received'
        CHECK (status IN ('received', 'analyzed', 'draft_reply', 'reply_sent', 'resolved', 'escalated')),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_observations_org ON observations_autorite(organization_id);
CREATE INDEX IF NOT EXISTS idx_observations_project ON observations_autorite(project_id);
CREATE INDEX IF NOT EXISTS idx_observations_status ON observations_autorite(status);
CREATE INDEX IF NOT EXISTS idx_observations_deadline ON observations_autorite(deadline_at);

-- ============================================================
-- 3. MÉTRÉS IFC
-- ============================================================

CREATE TABLE IF NOT EXISTS metres_ifc (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    source_ifc_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,

    -- Quantités globales
    nb_storeys INTEGER,
    nb_spaces INTEGER,
    sb_m2 NUMERIC(10,2),
    su_m2 NUMERIC(10,2),
    sre_m2 NUMERIC(10,2),
    volume_m3 NUMERIC(12,2),
    envelope_m2 NUMERIC(10,2),

    -- Détail
    by_storey JSONB DEFAULT '[]',           -- [{name, elevation_m, sb_m2, ...}]
    by_cfc JSONB DEFAULT '{}',              -- {"214": {surface_m2, volume_m3, count, ifc_classes}}

    -- Livrables
    pdf_path TEXT,
    dpgf_xlsx_path TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metres_org ON metres_ifc(organization_id);
CREATE INDEX IF NOT EXISTS idx_metres_project ON metres_ifc(project_id);
CREATE INDEX IF NOT EXISTS idx_metres_created ON metres_ifc(created_at DESC);

-- ============================================================
-- 4. SIMULATIONS ÉNERGÉTIQUES RAPIDES
-- ============================================================

CREATE TABLE IF NOT EXISTS simulations_rapides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    -- Inputs
    sre_m2 NUMERIC(10,2) NOT NULL,
    affectation TEXT NOT NULL,
    canton TEXT NOT NULL,
    standard TEXT NOT NULL,                  -- sia_380_1_neuf | minergie | ...
    operation_type TEXT,
    heating_vector TEXT,
    facteur_forme TEXT,
    fraction_ouvertures NUMERIC(4,2),

    -- Résultats variante principale
    qh_kwh_m2_an NUMERIC(8,2),
    ep_kwh_m2_an NUMERIC(8,2),
    energy_class TEXT CHECK (energy_class IN ('A', 'B', 'C', 'D', 'E', 'F', 'G')),
    compliant BOOLEAN,

    -- Variantes comparatives
    variants JSONB DEFAULT '[]',

    -- Détail calcul
    ua_total_wk NUMERIC(10,2),
    a_enveloppe_m2 NUMERIC(10,2),
    pertes_transmission_kwh NUMERIC(12,0),
    pertes_ventilation_kwh NUMERIC(12,0),

    pdf_path TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_simrapides_org ON simulations_rapides(organization_id);
CREATE INDEX IF NOT EXISTS idx_simrapides_project ON simulations_rapides(project_id);

-- ============================================================
-- 5. VUE AGRÉGÉE "TABLEAU DE BORD CONFORMITÉ MULTI-PROJETS"
-- ============================================================

CREATE OR REPLACE VIEW project_compliance_dashboard AS
SELECT
    p.id AS project_id,
    p.organization_id,
    p.name AS project_name,
    p.canton,
    p.affectation,
    p.status AS project_status,
    p.created_at,

    -- IDC
    (SELECT classification_status FROM idc_declarations_v3 d
     WHERE d.organization_id = p.organization_id
       AND d.building_id IN (SELECT id FROM idc_buildings WHERE project_id = p.id)
     ORDER BY year DESC LIMIT 1) AS idc_latest_status,

    (SELECT year FROM idc_declarations_v3 d
     WHERE d.organization_id = p.organization_id
       AND d.building_id IN (SELECT id FROM idc_buildings WHERE project_id = p.id)
     ORDER BY year DESC LIMIT 1) AS idc_latest_year,

    -- Thermique
    (SELECT compliant FROM thermic_simulations t
     WHERE t.project_id = p.id ORDER BY created_at DESC LIMIT 1) AS thermique_compliant,

    (SELECT energy_class FROM thermic_simulations t
     WHERE t.project_id = p.id ORDER BY created_at DESC LIMIT 1) AS energy_class,

    -- Structure
    (SELECT engineer_validated FROM structural_analyses s
     WHERE s.project_id = p.id ORDER BY created_at DESC LIMIT 1) AS structure_validated,

    -- AEAI
    (SELECT COUNT(*) FROM aeai_checklists a
     WHERE a.project_id = p.id AND a.status = 'validated') AS nb_aeai_validees,

    -- Dossier enquête
    (SELECT status FROM dossiers_enquete d
     WHERE d.project_id = p.id ORDER BY created_at DESC LIMIT 1) AS dossier_enquete_status,

    (SELECT coverage_pct FROM dossiers_enquete d
     WHERE d.project_id = p.id ORDER BY created_at DESC LIMIT 1) AS dossier_coverage_pct,

    -- Observations en attente
    (SELECT COUNT(*) FROM observations_autorite o
     WHERE o.project_id = p.id AND o.status IN ('received', 'analyzed', 'draft_reply')) AS nb_observations_ouvertes,

    (SELECT MIN(deadline_at) FROM observations_autorite o
     WHERE o.project_id = p.id AND o.status IN ('received', 'analyzed', 'draft_reply')) AS observation_prochaine_deadline,

    -- Impacts réglementaires
    (SELECT COUNT(*) FROM regulatory_impacts r
     WHERE r.project_id = p.id AND r.status IN ('new', 'action_required')) AS nb_impacts_reglementaires_actifs,

    -- Dernière MàJ
    GREATEST(
        COALESCE((SELECT MAX(updated_at) FROM dossiers_enquete WHERE project_id = p.id), p.created_at),
        COALESCE((SELECT MAX(updated_at) FROM observations_autorite WHERE project_id = p.id), p.created_at),
        COALESCE((SELECT MAX(updated_at) FROM thermic_simulations WHERE project_id = p.id), p.created_at),
        p.updated_at,
        p.created_at
    ) AS last_activity_at

FROM projects p;

-- ============================================================
-- 6. ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE dossiers_enquete ENABLE ROW LEVEL SECURITY;
ALTER TABLE observations_autorite ENABLE ROW LEVEL SECURITY;
ALTER TABLE metres_ifc ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulations_rapides ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "dossiers_enquete_own_org" ON dossiers_enquete;
CREATE POLICY "dossiers_enquete_own_org" ON dossiers_enquete FOR ALL
    USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "observations_own_org" ON observations_autorite;
CREATE POLICY "observations_own_org" ON observations_autorite FOR ALL
    USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "metres_own_org" ON metres_ifc;
CREATE POLICY "metres_own_org" ON metres_ifc FOR ALL
    USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "simrapides_own_org" ON simulations_rapides;
CREATE POLICY "simrapides_own_org" ON simulations_rapides FOR ALL
    USING (organization_id = current_organization_id());

-- ============================================================
-- 7. TRIGGERS updated_at
-- ============================================================

DROP TRIGGER IF EXISTS trigger_dossiers_enquete_updated ON dossiers_enquete;
CREATE TRIGGER trigger_dossiers_enquete_updated
    BEFORE UPDATE ON dossiers_enquete
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trigger_observations_updated ON observations_autorite;
CREATE TRIGGER trigger_observations_updated
    BEFORE UPDATE ON observations_autorite
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

COMMIT;
