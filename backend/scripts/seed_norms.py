"""Script de seed des normes suisses initiales.

Usage :
    cd backend
    python -m scripts.seed_norms
"""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def seed_norms():
    from app.ch.norms_catalog import all_seed_norms
    from app.database import get_supabase_admin

    admin = get_supabase_admin()
    all_norms = all_seed_norms()
    inserted = 0
    skipped = 0

    for norm in all_norms:
        # Vérifie si déjà présente (par reference)
        existing = admin.table("regulatory_norms").select("id").eq("reference", norm["reference"]).maybe_single().execute()
        if existing.data:
            skipped += 1
            continue
        try:
            admin.table("regulatory_norms").insert({
                **norm,
                "last_checked": "now()",
            }).execute()
            inserted += 1
            logger.info(f"✓ Inséré : {norm['reference']} - {norm['title'][:60]}")
        except Exception as e:
            logger.error(f"✗ Erreur {norm['reference']}: {e}")

    logger.info(f"\n=== Seed terminé ===")
    logger.info(f"Insérées : {inserted}")
    logger.info(f"Déjà présentes : {skipped}")
    logger.info(f"Total catalogue : {len(all_norms)}")


if __name__ == "__main__":
    try:
        seed_norms()
    except Exception as e:
        logger.exception("Seed échoué")
        sys.exit(1)
