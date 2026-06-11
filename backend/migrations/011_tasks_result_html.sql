-- 011 — Stocke le HTML complet du livrable sur la tâche
--
-- L'export Word repose aujourd'hui sur un « sidecar » HTML en storage
-- ({org}/_docx_src/{task_id}.html). Si ce fichier manque (course, transitoire,
-- run antérieur), l'export retombe sur l'aperçu TEXTE → Word appauvri.
-- On persiste le corps HTML directement sur la tâche (transactionnel, fiable) ;
-- l'export le lit en priorité, le sidecar restant un second filet.
--
-- Le code dégrade proprement si la colonne n'existe pas encore (écriture et
-- lecture protégées) : la migration peut être appliquée sans coupure.

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS result_html TEXT;
