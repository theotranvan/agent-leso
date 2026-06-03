-- Incrément atomique du compteur de tâches mensuel.
-- Évite les pertes de mise à jour quand plusieurs ingénieurs de la même
-- organisation terminent des tâches simultanément (read-modify-write → race).
-- Le code applicatif appelle cette fonction via RPC, avec fallback si absente.

CREATE OR REPLACE FUNCTION increment_tasks_used(p_org_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    new_value INTEGER;
BEGIN
    UPDATE organizations
       SET tasks_used_this_month = COALESCE(tasks_used_this_month, 0) + 1
     WHERE id = p_org_id
    RETURNING tasks_used_this_month INTO new_value;
    RETURN new_value;
END;
$$;
