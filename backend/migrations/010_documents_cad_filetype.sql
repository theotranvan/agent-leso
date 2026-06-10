-- 010 — Autorise le type de fichier 'cad' (plans DXF/DWG)
--
-- Le relevé thermique / métrés 2D enregistre les plans CAO avec
-- documents.file_type = 'cad' (cf. EXT_TO_TYPE : dxf/dwg → 'cad'). La contrainte
-- CHECK d'origine (001) ne listait pas 'cad' → l'upload d'un DXF/DWG échouait
-- côté base ("Échec de l'enregistrement du document (base de données)").
--
-- Idempotent et robuste : on supprime toute contrainte CHECK portant sur
-- file_type (quel que soit son nom auto-généré), puis on la recrée avec 'cad'.

DO $$
DECLARE
    c text;
BEGIN
    FOR c IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'documents'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%file_type%'
    LOOP
        EXECUTE format('ALTER TABLE documents DROP CONSTRAINT %I', c);
    END LOOP;
END $$;

ALTER TABLE documents
    ADD CONSTRAINT documents_file_type_check
    CHECK (file_type IN ('pdf', 'docx', 'ifc', 'bcf', 'xlsx', 'image', 'cad'));
