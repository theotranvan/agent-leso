-- ============================================================
-- BET Agent V2 - Migration CH + moteur réglementaire + GAPs
-- À exécuter APRÈS 001_initial_schema.sql
-- ============================================================

-- ============================================================
-- 1. EXTENSIONS ORGANISATIONS POUR LA SUISSE
-- ============================================================

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS country TEXT DEFAULT 'CH' CHECK (country IN ('CH', 'FR')),
    ADD COLUMN IF NOT EXISTS canton TEXT,  -- 'GE', 'VD', 'NE', 'FR', 'VS', 'BE', 'JU', 'ZH', etc.
    ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'fr' CHECK (language IN ('fr', 'de', 'it', 'en')),
    ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'CHF' CHECK (currency IN ('CHF', 'EUR')),
    ADD COLUMN IF NOT EXISTS vat_number TEXT,     -- CHE-123.456.789 (CH) ou FR12345678901 (FR)
    ADD COLUMN IF NOT EXISTS vat_rate NUMERIC(4,2) DEFAULT 8.10,  -- TVA CH standard 2024+
    ADD COLUMN IF NOT EXISTS iban TEXT,
    ADD COLUMN IF NOT EXISTS address TEXT,
    ADD COLUMN IF NOT EXISTS postal_code TEXT,
    ADD COLUMN IF NOT EXISTS city TEXT;

-- Pour projets : canton + affectation + zone
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS canton TEXT,
    ADD COLUMN IF NOT EXISTS commune TEXT,
    ADD COLUMN IF NOT EXISTS zone_affectation TEXT,  -- zone de développement, zone villa, etc.
    ADD COLUMN IF NOT EXISTS affectation TEXT,       -- 'logement_collectif', 'logement_individuel', 'bureau', 'erp', 'industriel', 'mixte'
    ADD COLUMN IF NOT EXISTS operation_type TEXT,    -- 'neuf', 'renovation', 'transformation', 'surelevation'
    ADD COLUMN IF NOT EXISTS sre_m2 NUMERIC(10,2),  -- Surface de Référence Énergétique
    ADD COLUMN IF NOT EXISTS nb_logements INTEGER,
    ADD COLUMN IF NOT EXISTS standard_energetique TEXT,  -- 'sia_380_1', 'minergie', 'minergie_p', 'minergie_a', 'cecb'
    ADD COLUMN IF NOT EXISTS climate_station TEXT,       -- station météo SIA 2028 la plus proche
    ADD COLUMN IF NOT EXISTS phase_sia TEXT;             -- '31', '32', '33', '41', '52', '53' phases SIA 102

-- ============================================================
-- 2. MOTEUR RÉGLEMENTAIRE SUISSE ROMANDE
-- ============================================================

CREATE TABLE IF NOT EXISTS regulatory_norms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    authority TEXT NOT NULL,        -- 'Confédération', 'Canton-GE', 'Canton-VD', 'SIA', 'AEAI', 'OFEN', 'Electrosuisse', 'MINERGIE'
    jurisdiction TEXT[] NOT NULL,   -- ['CH'], ['CH-GE'], ['CH-GE','CH-VD']
    reference TEXT NOT NULL,        -- 'SIA 380/1:2016', 'LEn-GE', 'AEAI 15-15f'
    title TEXT NOT NULL,
    domain TEXT[] NOT NULL,         -- ['thermique', 'structure', 'incendie', 'electricite', 'accessibilite', 'acoustique', 'general']
    effective_from DATE,
    effective_to DATE,
    public_access BOOLEAN DEFAULT TRUE,
    quotable BOOLEAN DEFAULT TRUE,  -- false pour SIA, NIBT, AEAI privées
    source_url TEXT,
    summary TEXT,                   -- résumé maison, toujours autorisé
    content_full TEXT,              -- NULL si non quotable
    version TEXT,
    last_checked TIMESTAMPTZ DEFAULT NOW(),
    superseded_by UUID REFERENCES regulatory_norms(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_norms_authority ON regulatory_norms(authority);
CREATE INDEX IF NOT EXISTS idx_norms_domain ON regulatory_norms USING gin(domain);
CREATE INDEX IF NOT EXISTS idx_norms_jurisdiction ON regulatory_norms USING gin(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_norms_reference ON regulatory_norms(reference);

CREATE TABLE IF NOT EXISTS regulatory_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    norm_id UUID REFERENCES regulatory_norms(id) ON DELETE CASCADE,
    change_type TEXT NOT NULL CHECK (change_type IN ('published', 'amended', 'repealed', 'superseded')),
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    impact_level TEXT NOT NULL CHECK (impact_level IN ('CRITIQUE', 'IMPORTANT', 'INFO')),
    impact_summary TEXT,
    affected_project_types TEXT[],
    source_url TEXT,
    raw_data JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_changes_detected ON regulatory_changes(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_changes_impact ON regulatory_changes(impact_level, detected_at DESC);

-- Liens projet → normes citées (pour notifier en cas de changement)
CREATE TABLE IF NOT EXISTS project_norms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    norm_id UUID REFERENCES regulatory_norms(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    cited_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, norm_id, document_id)
);

-- ============================================================
-- 3. MODULE IDC GENÈVE
-- ============================================================

CREATE TABLE IF NOT EXISTS idc_buildings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    ega TEXT,                       -- Identifiant Genevois du bâtiment (EGID)
    address TEXT NOT NULL,
    postal_code TEXT,
    sre_m2 NUMERIC(10,2) NOT NULL,  -- Surface de Référence Énergétique
    heating_energy_vector TEXT,     -- 'gaz', 'mazout', 'chauffage_distance', 'pac', 'pellet', 'electrique'
    building_year INTEGER,
    nb_logements INTEGER,
    regie_name TEXT,
    regie_email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_idc_buildings_org ON idc_buildings(organization_id);
CREATE INDEX IF NOT EXISTS idx_idc_buildings_ega ON idc_buildings(ega);

CREATE TABLE IF NOT EXISTS idc_annual_declarations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    building_id UUID NOT NULL REFERENCES idc_buildings(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    period_start DATE,
    period_end DATE,
    consumption_kwh NUMERIC(12,2),
    consumption_raw_unit TEXT,       -- 'litres', 'm3', 'kwh', 'kg'
    consumption_raw_value NUMERIC(12,2),
    degree_days NUMERIC(8,2),        -- DJ chauffage station météo
    idc_mj_m2 NUMERIC(8,2),          -- IDC calculé en MJ/m²/an (unité genevoise)
    idc_threshold_mj_m2 NUMERIC(8,2),-- seuil applicable selon LEn-GE
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'validated', 'submitted')),
    submitted_at TIMESTAMPTZ,
    form_pdf_url TEXT,
    notes TEXT,
    source_documents UUID[] DEFAULT '{}', -- IDs documents (factures) utilisés
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(building_id, year)
);

CREATE INDEX IF NOT EXISTS idx_idc_decl_building ON idc_annual_declarations(building_id);
CREATE INDEX IF NOT EXISTS idx_idc_decl_year ON idc_annual_declarations(year);

-- ============================================================
-- 4. AEAI - CHECKLISTS INCENDIE
-- ============================================================

CREATE TABLE IF NOT EXISTS aeai_checklists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    building_type TEXT NOT NULL,    -- 'habitation_faible', 'habitation_moyenne', 'habitation_elevee', 'erp', 'industriel', 'parking'
    height_class TEXT,              -- 'faible_<11m', 'moyenne_11-30m', 'elevee_>30m'
    nb_occupants_max INTEGER,
    items JSONB NOT NULL,           -- [{id, reference, title, status, notes}]
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'completed', 'validated')),
    validated_by UUID REFERENCES users(id),
    validated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aeai_org ON aeai_checklists(organization_id);

-- ============================================================
-- 5. THERMIQUE - MODÈLES INTERMÉDIAIRES
-- ============================================================

CREATE TABLE IF NOT EXISTS thermal_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    source_ifc_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    canton TEXT NOT NULL,
    affectation TEXT,
    operation_type TEXT,             -- neuf / renovation
    standard TEXT,                   -- 'sia_380_1', 'cecb', 'minergie_p', etc.
    zones JSONB DEFAULT '[]',        -- [{id, name, area, volume, temp_setpoint, affectation}]
    walls JSONB DEFAULT '[]',        -- [{id, type, area, u_value, layers, orientation}]
    openings JSONB DEFAULT '[]',     -- [{id, type, area, u_value, g_value}]
    thermal_bridges JSONB DEFAULT '[]',
    systems JSONB DEFAULT '{}',      -- heating, ventilation, ECS
    hypotheses JSONB DEFAULT '{}',   -- overrides utilisateur des défauts SIA
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'ready', 'sent_to_engine', 'results_received', 'completed')),
    engine_connector TEXT,           -- 'lesosai_stub', 'lesosai_file', 'internal'
    results JSONB DEFAULT '{}',      -- Qh, Qww, E, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_thermal_org ON thermal_models(organization_id);
CREATE INDEX IF NOT EXISTS idx_thermal_project ON thermal_models(project_id);

-- ============================================================
-- 6. STRUCTURE - MODÈLES SAF
-- ============================================================

CREATE TABLE IF NOT EXISTS structural_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    source_ifc_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    referentiel TEXT DEFAULT 'sia' CHECK (referentiel IN ('sia', 'eurocode')),
    material_default TEXT,           -- 'ba', 'acier', 'bois', 'mixte'
    exposure_class TEXT,             -- XC1, XC2... selon SIA 262
    consequence_class TEXT,          -- CC1, CC2, CC3
    seismic_zone TEXT,               -- Z1a, Z1b, Z2, Z3a, Z3b
    nodes JSONB DEFAULT '[]',
    members JSONB DEFAULT '[]',
    supports JSONB DEFAULT '[]',
    load_cases JSONB DEFAULT '[]',
    combinations JSONB DEFAULT '[]',
    saf_file_url TEXT,
    results_file_url TEXT,
    results_parsed JSONB DEFAULT '{}',
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'saf_generated', 'awaiting_engineer', 'results_imported', 'note_generated', 'validated')),
    engineer_validated_by UUID REFERENCES users(id),
    engineer_validated_at TIMESTAMPTZ,
    double_check_result JSONB DEFAULT '{}',  -- divergences détectées par solveur analytique
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_structural_org ON structural_models(organization_id);
CREATE INDEX IF NOT EXISTS idx_structural_project ON structural_models(project_id);

-- ============================================================
-- 7. PRÉ-BIM - MODÈLES IFC GÉNÉRÉS
-- ============================================================

CREATE TABLE IF NOT EXISTS bim_premodels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    source_inputs JSONB DEFAULT '{}',  -- {pdfs: [ids], dxfs: [ids], program_text: "...", surfaces_table: [...]}
    generated_ifc_url TEXT,
    generation_report JSONB DEFAULT '{}', -- {confidence: 0.75, validated_elements: [...], warnings: [...]}
    validated BOOLEAN DEFAULT FALSE,
    validated_by UUID REFERENCES users(id),
    validated_at TIMESTAMPTZ,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'extracting', 'generating', 'awaiting_review', 'validated', 'rejected')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bim_premodels_org ON bim_premodels(organization_id);

-- ============================================================
-- 8. LESOSAI CONNECTOR LOG (traçabilité des échanges)
-- ============================================================

CREATE TABLE IF NOT EXISTS lesosai_exchanges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    thermal_model_id UUID REFERENCES thermal_models(id) ON DELETE CASCADE,
    direction TEXT NOT NULL CHECK (direction IN ('out', 'in')),  -- out = vers Lesosai, in = depuis Lesosai
    mode TEXT NOT NULL,              -- 'stub', 'file_xml', 'api'
    payload_url TEXT,                -- storage_path du fichier échangé
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 9. RLS
-- ============================================================

ALTER TABLE idc_buildings ENABLE ROW LEVEL SECURITY;
ALTER TABLE idc_annual_declarations ENABLE ROW LEVEL SECURITY;
ALTER TABLE aeai_checklists ENABLE ROW LEVEL SECURITY;
ALTER TABLE thermal_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE structural_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE bim_premodels ENABLE ROW LEVEL SECURITY;
ALTER TABLE lesosai_exchanges ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_norms ENABLE ROW LEVEL SECURITY;

-- regulatory_norms et regulatory_changes : lecture pour tous les authentifiés, pas de filtre org
ALTER TABLE regulatory_norms ENABLE ROW LEVEL SECURITY;
ALTER TABLE regulatory_changes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "idc_buildings_own_org" ON idc_buildings;
CREATE POLICY "idc_buildings_own_org" ON idc_buildings FOR ALL
    USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "idc_decl_own_org" ON idc_annual_declarations;
CREATE POLICY "idc_decl_own_org" ON idc_annual_declarations FOR ALL
    USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "aeai_own_org" ON aeai_checklists;
CREATE POLICY "aeai_own_org" ON aeai_checklists FOR ALL
    USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "thermal_own_org" ON thermal_models;
CREATE POLICY "thermal_own_org" ON thermal_models FOR ALL
    USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "structural_own_org" ON structural_models;
CREATE POLICY "structural_own_org" ON structural_models FOR ALL
    USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "bim_premodels_own_org" ON bim_premodels;
CREATE POLICY "bim_premodels_own_org" ON bim_premodels FOR ALL
    USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "lesosai_own_org" ON lesosai_exchanges;
CREATE POLICY "lesosai_own_org" ON lesosai_exchanges FOR ALL
    USING (organization_id = current_organization_id());

DROP POLICY IF EXISTS "project_norms_own_org" ON project_norms;
CREATE POLICY "project_norms_own_org" ON project_norms FOR ALL
    USING (project_id IN (SELECT id FROM projects WHERE organization_id = current_organization_id()));

-- Normes réglementaires visibles par tous les utilisateurs authentifiés
DROP POLICY IF EXISTS "norms_read_all" ON regulatory_norms;
CREATE POLICY "norms_read_all" ON regulatory_norms FOR SELECT
    USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS "changes_read_all" ON regulatory_changes;
CREATE POLICY "changes_read_all" ON regulatory_changes FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- ============================================================
-- 10. TRIGGERS updated_at
-- ============================================================

DROP TRIGGER IF EXISTS trigger_idc_buildings_updated ON idc_buildings;
CREATE TRIGGER trigger_idc_buildings_updated
    BEFORE UPDATE ON idc_buildings
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trigger_thermal_updated ON thermal_models;
CREATE TRIGGER trigger_thermal_updated
    BEFORE UPDATE ON thermal_models
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trigger_structural_updated ON structural_models;
CREATE TRIGGER trigger_structural_updated
    BEFORE UPDATE ON structural_models
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- ============================================================
-- 11. TASK TYPES V2 - étendre le CHECK constraint
-- ============================================================

-- Les nouveaux task_types sont gérés dans le CODE (Literal Pydantic), pas au niveau DB
-- car la colonne task_type est déjà TEXT sans check contraint strict.

COMMIT;
