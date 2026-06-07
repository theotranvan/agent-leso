-- ============================================================
-- 006_plan_rename.sql — Renommage des forfaits
--   starter → solo, pro → bureau (enterprise inchangé)
--
-- La migration 001 contraignait plan ∈ (starter, pro, enterprise).
-- L'application utilise désormais le vocabulaire solo / bureau / enterprise.
-- On migre les lignes existantes, on met à jour le défaut, et on recrée
-- la contrainte CHECK sur le nouveau vocabulaire.
--
-- Idempotent / sans perte : ne fait que renommer des valeurs et la contrainte.
-- ============================================================

-- 1. Retirer l'ancienne contrainte (sinon l'UPDATE vers 'solo' échoue)
ALTER TABLE organizations DROP CONSTRAINT IF EXISTS organizations_plan_check;

-- 2. Migrer les valeurs existantes vers le nouveau vocabulaire
UPDATE organizations SET plan = 'solo'   WHERE plan = 'starter';
UPDATE organizations SET plan = 'bureau' WHERE plan = 'pro';
-- 'enterprise' reste 'enterprise'

-- 3. Nouveau défaut
ALTER TABLE organizations ALTER COLUMN plan SET DEFAULT 'solo';

-- 4. Recréer la contrainte sur le nouveau vocabulaire
ALTER TABLE organizations
    ADD CONSTRAINT organizations_plan_check
    CHECK (plan IN ('solo', 'bureau', 'enterprise'));
