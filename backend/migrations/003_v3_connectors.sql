-- ============================================================
-- BET Agent V3 - Migration connecteurs
-- À exécuter APRÈS 002_ch_v2_schema.sql
--
-- Tables ajoutées :
--   * thermic_simulations     : historique des simulations thermiques
--   * structural_analyses     : historique des analyses structurelles
--   * idc_declarations_v3     : déclarations IDC détaillées (superset de V2)
--   * regulatory_impacts      : impacts réglementaires par projet
-- ============================================================

-- ============================================================
-- 1. THERMIC SIMULATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS thermic_simulations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    thermal_model_id UUID REFERENCES thermal_models(id) ON DELETE SET NULL,
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,

    -- Connecteur utilisé
    connector_name TEXT NOT NULL,                -- gbxml_generator, cecb_parser, lesosai_watched_folder, stub
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'timeout')),

    -- Entrées
    canton TEXT NOT NULL,
    affectation TEXT NOT NULL,
    operation_type TEXT DEFAULT 'neuf',
    standard TEXT DEFAULT 'sia_380_1',
    sre_m2 NUMERIC(10,2),
    heating_vector TEXT,

    -- Résultats
    qh_kwh_m2_an NUMERIC(8,2),
    ep_kwh_m2_an NUMERIC(8,2),
    idc_kwh_m2_an NUMERIC(8,2),
    qh_limite_kwh_m2_an NUMERIC(8,2),
    energy_class TEXT CHECK (energy_class IN ('A', 'B', 'C', 'D', 'E', 'F', 'G')),
    compliant BOOLEAN,
    computation_seconds NUMERIC(10,3),

    -- Fichiers générés
    gbxml_storage_path TEXT,
    result_storage_path TEXT,      -- PDF justificatif ou XML CECB
    report_storage_path TEXT,

    warnings JSONB DEFAULT '[]',
    raw_output JSONB DEFAULT '{}',
    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_thermic_sim_org ON thermic_simulations(organization_id);
CREATE INDEX IF NOT EXISTS idx_thermic_sim_project ON thermic_simulations(project_id);
CREATE INDEX IF NOT EXISTS idx_thermic_sim_status ON thermic_simulations(status);
CREATE INDEX IF NOT EXISTS idx_thermic_sim_created ON thermic_simulations(created_at DESC);

-- ============================================================
-- 2. STRUCTURAL ANALYSES
-- ============================================================

CREATE TABLE IF NOT EXISTS structural_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    structural_model_id UUID REFERENCES structural_models(id) ON DELETE SET NULL,

    connector_name TEXT NOT NULL,      -- saf_generator, scia_watched_folder, robot_csv_option_c, stub
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'saf_generated', 'awaiting_engineer', 'results_imported',
                          'completed', 'failed', 'timeout')),

    -- Paramètres
    referentiel TEXT DEFAULT 'sia',
    exposure_class TEXT DEFAULT 'XC2',
    consequence_class TEXT DEFAULT 'CC2',
    seismic_zone TEXT DEFAULT 'Z1b',

    -- Résultats globaux
    compliant BOOLEAN,
    max_utilization NUMERIC(6,3),
    nb_checks INTEGER DEFAULT 0,
    nb_anomalies INTEGER DEFAULT 0,
    max_divergence_pct NUMERIC(6,2),
    computation_seconds NUMERIC(10,3),

    -- Détails par élément (JSONB pour flexibilité)
    member_checks JSONB DEFAULT '[]',
    anomalies JSONB DEFAULT '[]',

    -- Fichiers
    saf_input_storage_path TEXT,
    saf_output_storage_path TEXT,
    note_pdf_storage_path TEXT,

    -- Validation humaine obligatoire
    engineer_validated BOOLEAN DEFAULT FALSE,
    engineer_validated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    engineer_validated_at TIMESTAMPTZ,
    engineer_name TEXT,

    warnings JSONB DEFAULT '[]',
    raw_output JSONB DEFAULT '{}',
    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_struct_an_org ON structural_analyses(organization_id);
CREATE INDEX IF NOT EXISTS idx_struct_an_project ON structural_analyses(project_id);
CREATE INDEX IF NOT EXISTS idx_struct_an_status ON structural_analyses(status);

-- ============================================================
-- 3. IDC DECLARATIONS v3 (superset de la table v2)
-- ============================================================

CREATE TABLE IF NOT EXISTS idc_declarations_v3 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    building_id UUID NOT NULL REFERENCES idc_buildings(id) ON DELETE CASCADE,
    legacy_declaration_id UUID REFERENCES idc_annual_declarations(id) ON DELETE SET NULL,

    year INTEGER NOT NULL,
    vector TEXT NOT NULL,

    -- Consommations extraites des factures
    consumptions JSONB NOT NULL DEFAULT '[]',     -- [{raw_value, raw_unit, period_start, period_end, source_doc_id, confidence}]
    total_energy_kwh NUMERIC(14,2),

    -- Calcul IDC
    idc_raw_kwh_m2_an NUMERIC(8,2),
    idc_normalized_kwh_m2_an NUMERIC(8,2),
    idc_normalized_mj_m2_an NUMERIC(10,2),
    climate_correction_factor NUMERIC(6,4),
    dju_normal NUMERIC(8,2),
    dju_year_measured NUMERIC(8,2),

    -- Classification
    classification_status TEXT
        CHECK (classification_status IN ('OK', 'ATTENTION', 'ASSAINISSEMENT_RECOMMANDE',
                                         'ASSAINISSEMENT_OBLIGATOIRE', 'CRITIQUE')),
    classification_label TEXT,
    action_required TEXT,

    -- État déclaration
    status TEXT DEFAULT 'draft'
        CHECK (status IN ('draft', 'validated', 'submitted', 'archived')),
    submitted_at TIMESTAMPTZ,
    submitted_by UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Fichiers
    ocen_form_pdf_path TEXT,
    source_document_ids UUID[] DEFAULT '{}',

    warnings JSONB DEFAULT '[]',
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(building_id, year)
);

CREATE INDEX IF NOT EXISTS idx_idc_v3_org ON idc_declarations_v3(organization_id);
CREATE INDEX IF NOT EXISTS idx_idc_v3_building ON idc_declarations_v3(building_id);
CREATE INDEX IF NOT EXISTS idx_idc_v3_year ON idc_declarations_v3(year);
CREATE INDEX IF NOT EXISTS idx_idc_v3_status ON idc_declarations_v3(classification_status);

-- ============================================================
-- 4. REGULATORY IMPACTS - traçabilité des impacts normes → projets
-- ============================================================

CREATE TABLE IF NOT EXISTS regulatory_impacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    norm_id UUID REFERENCES regulatory_norms(id) ON DELETE SET NULL,
    change_id UUID REFERENCES regulatory_changes(id) ON DELETE SET NULL,

    impact_level TEXT NOT NULL CHECK (impact_level IN ('CRITIQUE', 'IMPORTANT', 'INFO')),
    impact_description TEXT,
    affected_livrables TEXT[] DEFAULT '{}',  -- ['justificatif_sia_380_1', 'note_structure', ...]

    status TEXT DEFAULT 'new'
        CHECK (status IN ('new', 'acknowledged', 'action_required', 'resolved', 'ignored')),
    acknowledged_by UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMPTZ,
    resolution_notes TEXT,

    detected_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reg_impact_org ON regulatory_impacts(organization_id);
CREATE INDEX IF NOT EXISTS idx_reg_impact_project ON regulatory_impacts(project_id);
CREATE INDEX IF NOT EXISTS idx_reg_impact_status ON regulatory_impacts(status);
CREATE INDEX IF NOT EXISTS idx_reg_impact_level ON regulatory_impacts(impact_level);

-- ============================================================
-- 5. ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE thermic_simulations ENABLE ROW LEVEL SECURITY;
ALTER TABLE structural_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE idc_declarations_v3 ENABLE ROW LEVEL SECURITY;
ALTER TABLE regulatory_impacts ENABLE ROW LEVEL SECURITY;

-- thermic_simulations
DROP POLICY IF EXISTS "thermic_sim_own_org" ON thermic_simulations;
CREATE POLICY "thermic_sim_own_org" ON thermic_simulations FOR ALL
    USING (organization_id = current_organization_id());

-- structural_analyses
DROP POLICY IF EXISTS "struct_analyses_own_org" ON structural_analyses;
CREATE POLICY "struct_analyses_own_org" ON structural_analyses FOR ALL
    USING (organization_id = current_organization_id());

-- idc_declarations_v3
DROP POLICY IF EXISTS "idc_v3_own_org" ON idc_declarations_v3;
CREATE POLICY "idc_v3_own_org" ON idc_declarations_v3 FOR ALL
    USING (organization_id = current_organization_id());

-- regulatory_impacts
DROP POLICY IF EXISTS "reg_impact_own_org" ON regulatory_impacts;
CREATE POLICY "reg_impact_own_org" ON regulatory_impacts FOR ALL
    USING (organization_id = current_organization_id());

-- ============================================================
-- 6. TRIGGERS updated_at
-- ============================================================

DROP TRIGGER IF EXISTS trigger_thermic_sim_updated ON thermic_simulations;
CREATE TRIGGER trigger_thermic_sim_updated
    BEFORE UPDATE ON thermic_simulations
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trigger_struct_an_updated ON structural_analyses;
CREATE TRIGGER trigger_struct_an_updated
    BEFORE UPDATE ON structural_analyses
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trigger_idc_v3_updated ON idc_declarations_v3;
CREATE TRIGGER trigger_idc_v3_updated
    BEFORE UPDATE ON idc_declarations_v3
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trigger_reg_impact_updated ON regulatory_impacts;
CREATE TRIGGER trigger_reg_impact_updated
    BEFORE UPDATE ON regulatory_impacts
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

COMMIT;
