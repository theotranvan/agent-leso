# BET Agent — SaaS IA pour bureaux d'études techniques (Suisse romande)

**Version 2.0** · Swiss-first · Genève, Vaud, Neuchâtel, Fribourg, Valais, Jura

BET Agent automatise la production documentaire et technique des bureaux d'études de la
construction : justificatifs thermiques SIA 380/1, notes de calcul structure SIA 260-267,
descriptifs CAN/SIA 451, déclarations IDC Genève, checklists AEAI, coordination BIM,
veille réglementaire fédérale et cantonale.

## Vue d'ensemble

| Module | Ce que l'agent fait | Ce que l'ingénieur garde |
|---|---|---|
| **Thermique SIA 380/1** | Prépare le modèle + génère fichier Lesosai + fiche saisie opérateur + justificatif final | Calcul officiel dans Lesosai + visa |
| **Structure SIA 260-267** | Génère le SAF (xlsx) pour Scia/RFEM + double-check analytique + note de calcul | Calcul logiciel + validation + visa |
| **Pré-BIM** | Extrait le programme + génère un IFC 4 orthogonal avec Psets thermiques | Enrichissement BIM + contrôle qualité |
| **IDC Genève** | Extrait factures chaufferie + calcule IDC MJ/m²/an + formulaire OCEN | Vérification + transmission officielle |
| **AEAI (incendie)** | Checklist auto par typologie + rapport PDF | Coordination avec expert incendie |
| **Contrôle cantonal** | Pré-contrôle LCI/LEn-GE/LDTR / LATC / LVLEne ... | Dépôt d'autorisation officiel |
| **Veille réglementaire CH** | Surveille Fedlex + 6 cantons romands quotidiennement | Arbitrage et action |

## Philosophie

- L'agent produit des brouillons à 80% prêts. L'ingénieur-architecte vérifie, complète, signe.
- La **responsabilité professionnelle** (signature, visa, assurance décennale) reste à l'humain qualifié.
- Les **calculs officiels** (Lesosai, Scia Engineer, Cedrus, Robot...) restent dans les logiciels métier.
- **Respect strict des licences** : SIA, AEAI et NIBT ne sont jamais reproduits textuellement, uniquement référencés.

## Stack technique

### Backend
- Python 3.12 · FastAPI · Gunicorn + Uvicorn
- Supabase (PostgreSQL + pgvector + pgcrypto + RLS multi-tenant)
- ARQ + Redis (queue asynchrone + cron)
- Anthropic SDK (Claude Opus 4.6 / Sonnet 4.6 / Haiku 4.5)
- OpenAI embeddings (text-embedding-3-small)
- IfcOpenShell · PyMuPDF · pdfplumber · Tesseract OCR
- WeasyPrint (PDF) · openpyxl (Excel)
- Stripe · Resend · Sentry

### Frontend
- Next.js 15 · React 19 · TypeScript
- Tailwind CSS 4 · shadcn/ui · Recharts · Lucide
- Supabase Auth (SSR + CSR)

### Déploiement
- Render Frankfurt (API + Worker + Redis)
- Vercel (Next.js)
- Supabase Pro · UptimeRobot

## Démarrage local

```bash
# 1. Clone et setup
git clone <repo> && cd bet-agent
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# Éditer les 2 fichiers

# 2. Migrations Supabase dans l'ordre
psql $SUPABASE_DB_URL -f backend/migrations/001_initial_schema.sql
psql $SUPABASE_DB_URL -f backend/migrations/002_ch_v2_schema.sql

# 3. Seed normes CH (fait aussi au premier démarrage si AUTO_SEED_NORMS=true)
cd backend && python -m scripts.seed_norms

# 4. Docker Compose (API + worker + Redis)
cd .. && docker-compose up -d

# 5. Frontend
cd frontend && npm install && npm run dev
```

Accès :
- Frontend : http://localhost:3000
- API docs : http://localhost:8000/docs (sauf prod)

## Variables d'environnement clés

```bash
# Backend (.env)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
RESEND_API_KEY=re_...
REDIS_URL=redis://redis:6379
ENCRYPTION_KEY=<32 bytes base64>
SENTRY_DSN=https://...@sentry.io/...
ENVIRONMENT=production
AUTO_SEED_NORMS=true
DEFAULT_COUNTRY=CH

# Frontend (.env.local)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_API_URL=https://api.bet-agent.ch
```

## Routing Claude (stratégie de coût)

| Task type | Modèle | Rationale |
|---|---|---|
| `justificatif_sia_380_1`, `note_calcul_sia_260_267`, `calcul_cecb` | **Opus 4.6** | Calculs critiques |
| `descriptif_can_sia_451`, `controle_reglementaire_geneve`, `prebim_generation`, `idc_geneve_rapport`, `aeai_rapport` | **Sonnet 4.6** | Production structurée |
| `idc_extraction_facture`, `veille_romande`, `aeai_checklist_generation` | **Haiku 4.5** | Opérations légères |

Coût LLM : 40-60 CHF/mois pour 300 tâches. Infra fixe : ~98 CHF/mois.

## Plans

| Plan | Prix | Tâches/mois | Fonctionnalités |
|---|---|---|---|
| Starter | 690 CHF | 500 | Tous modules CH, 1 utilisateur |
| Pro | 1 900 CHF | 2 000 | + veille quotidienne, multi-utilisateurs, 50 Go |
| Enterprise | 5 000 CHF | illimité | + SLA, account manager, intégrations |

## Cron jobs (worker ARQ)

- `06:00` — Veille Légifrance FR
- `06:30` — Veille CH romande (Fedlex + 6 cantons)
- Lundi `08:00` — Rapport hebdo
- 1er du mois `00:05` — Reset quotas

## Sécurité

RLS multi-tenant · JWT Supabase · Rate limiting · HSTS/CSP/X-Frame · pgcrypto · Audit log immutable · RGPD export/delete.

## Tests

```bash
cd backend && pytest && ruff check . && bandit -r app/
cd frontend && npm run typecheck && npm run lint && npm run build
```

## Incertitudes V2 à valider avec BET pilotes

1. **API Lesosai** — E4tech Software Lausanne à contacter (V2 fonctionne en mode fichier + fiche saisie).
2. **Règles CECB cantonales** — Cas d'obligation variables par canton.
3. **Seuils IDC Genève** — Valeurs exactes à confirmer avec OCEN (indicatives dans le code).
4. **Format structure** — SAF compatible Scia/RFEM. Si BET utilise Cedrus/Cubus, adapter.

## Responsabilité

L'agent produit des brouillons. L'ingénieur-architecte qualifié vérifie, complète, signe.
BET Agent ne remplace **jamais** : la signature d'ingénieur, la relation client, les calculs
dans logiciels métier, les visites chantier, la responsabilité décennale.

Contact : **team@bet-agent.ch**
