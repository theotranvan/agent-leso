-- ============================================================================
-- RÉINITIALISATION "VIERGE" de l'organisation de jc.szwed@conti-ing.ch
-- ============================================================================
-- À exécuter dans Supabase → SQL Editor.
--
-- Ce que fait ce script :
--   • Retrouve l'organisation rattachée au compte jc.szwed@conti-ing.ch
--   • SUPPRIME toutes les DONNÉES DE TEST de cette organisation (tâches,
--     projets, documents, modèles thermiques/structure, checklists AEAI,
--     bâtiments/déclarations IDC, pré-modèles BIM, échéances, notifications…)
--   • REMET À ZÉRO les compteurs de quota de l'organisation
--
-- Ce que le script NE supprime PAS :
--   • Les comptes utilisateurs (les 8 ingénieurs peuvent toujours se connecter)
--   • L'organisation elle-même
--   • Le catalogue de normes (données globales)
--
-- ⚠️ Tous les ingénieurs Conti partagent la MÊME organisation : ce reset
--    nettoie donc l'espace partagé pour TOUTE l'équipe (c'est l'objectif :
--    repartir d'un espace vierge avant le démarrage réel).
-- ============================================================================

DO $$
DECLARE
  v_org uuid;
  t text;
  -- Ordre important : enfants d'abord, "projects" en dernier (clés étrangères).
  tables text[] := ARRAY[
    'idc_annual_declarations',
    'idc_buildings',
    'aeai_checklists',
    'thermal_models',
    'lesosai_exchanges',
    'structural_models',
    'bim_premodels',
    'token_usage',
    'credit_packs',
    'project_deadlines',
    'notifications',
    'audit_logs',
    'regulatory_alerts_read',
    'tasks',
    'documents',
    'projects'
  ];
  v_count bigint;
BEGIN
  -- 1. Organisation de l'utilisateur (via l'email d'authentification Supabase)
  SELECT u.organization_id INTO v_org
  FROM public.users u
  JOIN auth.users au ON au.id = u.id
  WHERE au.email = 'jc.szwed@conti-ing.ch'
  LIMIT 1;

  IF v_org IS NULL THEN
    RAISE EXCEPTION 'Aucune organisation trouvée pour jc.szwed@conti-ing.ch '
                    '(vérifier que le compte existe dans public.users / auth.users)';
  END IF;

  RAISE NOTICE 'Organisation cible : %', v_org;

  -- 2. Suppression table par table (ignore les tables/colonnes absentes)
  FOREACH t IN ARRAY tables LOOP
    BEGIN
      EXECUTE format('DELETE FROM public.%I WHERE organization_id = $1', t) USING v_org;
      GET DIAGNOSTICS v_count = ROW_COUNT;
      RAISE NOTICE '  %-28s : % ligne(s) supprimée(s)', t, v_count;
    EXCEPTION
      WHEN undefined_table THEN
        RAISE NOTICE '  %-28s : table absente, ignorée', t;
      WHEN undefined_column THEN
        RAISE NOTICE '  %-28s : pas de colonne organization_id, ignorée', t;
    END;
  END LOOP;

  -- 3. Remise à zéro des compteurs de quota de l'organisation
  --    (on tente les deux conventions de nommage présentes en base)
  BEGIN
    EXECUTE 'UPDATE public.organizations SET tasks_used_this_month = 0 WHERE id = $1' USING v_org;
  EXCEPTION WHEN undefined_column THEN NULL; END;

  BEGIN
    EXECUTE 'UPDATE public.organizations SET tokens_used_this_month = 0 WHERE id = $1' USING v_org;
  EXCEPTION WHEN undefined_column THEN NULL; END;

  BEGIN
    EXECUTE 'UPDATE public.organizations SET tokens_used_current_month = 0 WHERE id = $1' USING v_org;
  EXCEPTION WHEN undefined_column THEN NULL; END;

  -- 4. Réinitialise l'onboarding pour que l'org reparte d'un état neuf
  BEGIN
    EXECUTE 'UPDATE public.organizations SET onboarded_at = NULL WHERE id = $1' USING v_org;
  EXCEPTION WHEN undefined_column THEN NULL; END;

  RAISE NOTICE 'Réinitialisation terminée pour l''organisation %.', v_org;
END $$;

-- ============================================================================
-- VÉRIFICATION (optionnel) — doit renvoyer 0 partout
-- ============================================================================
-- SELECT
--   (SELECT count(*) FROM public.tasks    t JOIN public.users u ON u.organization_id = t.organization_id JOIN auth.users au ON au.id = u.id WHERE au.email='jc.szwed@conti-ing.ch') AS taches,
--   (SELECT count(*) FROM public.projects p JOIN public.users u ON u.organization_id = p.organization_id JOIN auth.users au ON au.id = u.id WHERE au.email='jc.szwed@conti-ing.ch') AS projets;
