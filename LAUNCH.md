# Checklist de mise en production — AGENT LESO

Objectif : 8 ingénieurs de Conti peuvent se connecter et travailler.
Tout le code est prêt et testé. Il reste la **configuration d'infrastructure**
ci-dessous (à faire dans les dashboards Supabase / Render / Vercel).

---

## 0. Créer l'équipe Conti (8 ingénieurs, sans invitation email)

Tous les 8 partagent **une seule organisation** → ils voient et travaillent sur
les **mêmes projets**. Le 1er est admin, les 7 autres membres (accès complet).

```bash
cd backend
# avec les mêmes variables d'env que l'API (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, …)
python -m scripts.seed_team --org "Conti" \
  --emails "chef@conti.ch,ing2@conti.ch,ing3@conti.ch,ing4@conti.ch,ing5@conti.ch,ing6@conti.ch,ing7@conti.ch,ing8@conti.ch"
```

- Le script crée l'org + les 8 comptes (connexion immédiate, sans email de
  confirmation) et **affiche un tableau email / mot de passe** à distribuer.
- Idempotent : relançable sans créer de doublons.
- Concurrence : les 8 peuvent créer projets, documents et tâches **en même temps
  sur le même projet** sans collision (chaque tâche/document est une ligne
  indépendante ; le compteur de quota est incrémenté de façon atomique).
  Seule l'édition simultanée des *métadonnées* d'un même projet (nom, canton…)
  suit la règle « dernier qui enregistre gagne » — sans risque de corruption.

## 1. Supabase (le plus important pour l'équipe)

- [ ] **Storage** : un bucket **privé** nommé `bet-documents` existe.
- [ ] **Migrations DB appliquées** dans l'ordre : `001` → `008`
      (`backend/migrations/*.sql`). Vérifier que la table `projects` a bien
      les colonnes `canton`, `affectation`, `current_phase`.
- [ ] **Auth → URL Configuration** :
  - Site URL = l'URL Vercel de prod (ex. `https://agent-leso.vercel.app`)
  - Redirect URLs (allowlist) : ajouter
    - `https://<vercel>/auth/callback`
    - `https://<vercel>/accept-invite`
    - `https://<vercel>/reset-password`
- [ ] **Auth → Emails** : l'envoi d'emails fonctionne.
  ⚠️ Le service email Supabase par défaut est **fortement limité** (quelques
  mails/heure) → pour inviter 8 ingénieurs d'un coup, configurer un **SMTP
  custom** (Auth → SMTP Settings), sinon inviter par petits lots.
- [ ] Tester **un** email d'invitation avant le jour J.

## 2. Render (API + worker + Redis)

- [ ] Les 3 services tournent : `bet-agent-api`, `bet-agent-worker`, `bet-agent-redis`.
- [ ] **Variables d'env identiques sur l'API ET le worker** :
  `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
  `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`.
  (Si une manque sur le worker, les tâches restent en « En attente ».)
- [ ] `REDIS_URL` câblé automatiquement par le Blueprint (vérifier).
- [ ] (Sécurité, optionnel) `ALLOWED_ORIGINS` = URL Vercel pour verrouiller le
      CORS. Laisser vide = ouvert (fonctionne, moins strict).
- [ ] Health check vert : `GET /health` répond `{"status":"ok"}`.

## 3. Vercel (frontend)

- [ ] `NEXT_PUBLIC_API_URL` = URL de l'API Render **sans slash final**
      (ex. `https://bet-agent-api.onrender.com`).
- [ ] `NEXT_PUBLIC_SUPABASE_URL` et `NEXT_PUBLIC_SUPABASE_ANON_KEY` renseignés.
- [ ] Redéploiement effectué après tout changement de variable
      (ces variables sont compilées dans le build).

## 4. Smoke test final (5 min, à faire une fois tout déployé)

### Option automatique (recommandée) — depuis ta machine
```bash
cd backend
python scripts/smoke_e2e.py \
  --api https://bet-agent-api.onrender.com \
  --supabase https://<projet>.supabase.co --anon <SUPABASE_ANON_KEY> \
  --email ing2@conti.ch --password '<mot de passe seedé>'
```
Le script déroule tout le parcours (login → projet → simulation → tâche queue →
worker) et affiche PASS/FAIL par étape. 100% PASS = prêt pour l'équipe.

### Option manuelle

1. [ ] L'admin s'inscrit → arrive sur le tableau de bord.
2. [ ] Réglages → inviter 1 ingénieur → il reçoit l'email → définit son mot de
       passe → accède au même espace (mêmes projets).
3. [ ] Créer un projet (canton + affectation).
4. [ ] Générer une **Simulation énergétique rapide** → résultat Qh immédiat.
5. [ ] Lancer une tâche de queue (ex. CCTP) → passe « En cours » → « Terminée ».
6. [ ] Ouvrir la tâche terminée → télécharger le PDF.
7. [ ] Onglet « À valider » → approuver → « Dossier complet » télécharge le ZIP.

Si l'étape 5 reste bloquée en « En attente » → worker Render : vérifier les
variables d'env et les logs du service `bet-agent-worker`.

## 5. Bon à savoir

- **Plan starter = 500 tâches/mois** partagées par l'organisation. Pour 8
  ingénieurs actifs, surveiller le quota (tableau de bord) et passer au plan
  supérieur si besoin (nécessite Stripe configuré — non bloquant au lancement).
- **Stripe** non requis pour démarrer : la page Facturation affiche le quota,
  l'upgrade se configure plus tard.
