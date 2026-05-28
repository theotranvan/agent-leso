-- ============================================================
-- BET Agent V6 — Templates à charte client + knowledge_base
-- À exécuter APRÈS 005_token_quota.sql
-- ============================================================

-- Configuration de charte par organisation (logo, couleurs, signature)
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS branding_config JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN organizations.branding_config IS
    'Charte client : {logo_url, primary_color, accent_color, font_family, signature_block, footer_text, full_name, address, phone, website}. Utilisé par le système de templates PDF.';

-- Niveau de prestation par défaut sur les projets (pour CCTP/DPGF)
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS niveau_prestation_defaut TEXT DEFAULT 'standard';

COMMENT ON COLUMN projects.niveau_prestation_defaut IS
    'Niveau de prestation par défaut (economique/standard/premium) pour les livrables CCTP et DPGF.';

-- Données urbanistiques du projet (pour dossier enquête + contrôle réglementaire)
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS zone_affectation TEXT,
    ADD COLUMN IF NOT EXISTS surface_terrain_m2 NUMERIC,
    ADD COLUMN IF NOT EXISTS sbp_projetee_m2 NUMERIC,
    ADD COLUMN IF NOT EXISTS emprise_sol_m2 NUMERIC,
    ADD COLUMN IF NOT EXISTS hauteur_corniche_m NUMERIC,
    ADD COLUMN IF NOT EXISTS hauteur_faitage_m NUMERIC,
    ADD COLUMN IF NOT EXISTS nb_niveaux INTEGER;

COMMENT ON COLUMN projects.zone_affectation IS
    'Zone d''affectation (ex: 5e_zone GE, zone_habitation_moyenne_densite VD) pour contrôle indices IUS/COS.';
