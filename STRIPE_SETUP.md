# Configuration Stripe — LESO (de zéro)

Ce guide te fait passer d'aucun compte Stripe à un paiement fonctionnel.
Suis-le dans l'ordre. Compte **~45 min** la première fois.

> **Important** : commence **toujours en mode Test**. Tu ne passes en mode Live
> qu'à la toute fin, une fois que tout marche. Les objets créés en Test ne sont
> PAS visibles en Live : tu devras refaire produits + prix + webhook en Live.

---

## Ce que le code attend (vue d'ensemble)

8 variables d'environnement à renseigner sur ton hébergeur (Render) :

| Variable | Contenu | Où l'obtenir |
|---|---|---|
| `STRIPE_SECRET_KEY` | `sk_test_…` puis `sk_live_…` | Étape 2 |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…` | Étape 5 |
| `STRIPE_PRICE_STARTER` | `price_…` (Solo **mensuel**) | Étape 3 |
| `STRIPE_PRICE_PRO` | `price_…` (Bureau **mensuel**) | Étape 3 |
| `STRIPE_PRICE_ENTERPRISE` | `price_…` (Enterprise **mensuel**) | Étape 3 |
| `STRIPE_PRICE_STARTER_YEARLY` | `price_…` (Solo **annuel**) | Étape 3 |
| `STRIPE_PRICE_PRO_YEARLY` | `price_…` (Bureau **annuel**) | Étape 3 |
| `STRIPE_PRICE_ENTERPRISE_YEARLY` | `price_…` (Enterprise **annuel**) | Étape 3 |

> Les noms `STARTER / PRO` sont historiques : ils pointent vers tes produits
> **Solo / Bureau**. Pas besoin de les renommer.

Le **pack de tokens additionnels** (+100 livrables / 200 CHF) n'a **rien à créer** :
le code génère son prix à la volée.

---

## Étape 1 — Créer le compte

1. Va sur https://dashboard.stripe.com/register
2. Crée le compte avec ton email pro.
3. **Type d'entreprise = « Particulier / indépendant »** (pas « Société »).
   Tant que ton chiffre d'affaires est sous 100 000 CHF/an, tu opères en
   **raison individuelle** : nom + adresse personnels + **IBAN suisse perso**
   suffisent. **Pas besoin d'IDE ni d'inscription au RC** pour démarrer.
4. En haut à droite, vérifie que l'interrupteur **« Mode test »** est **activé**
   (toggle orange « Test mode »).

---

## Étape 2 — Récupérer la clé secrète (Test)

1. Menu **Développeurs → Clés API** (`/test/apikeys`).
2. Copie la **« Clé secrète »** (`sk_test_…`). *(La clé publiable n'est pas
   nécessaire : LESO redirige vers la page de paiement hébergée par Stripe.)*
3. Garde-la de côté → ce sera `STRIPE_SECRET_KEY`.

---

## Étape 3 — Créer les 3 produits et leurs 6 prix

Menu **Catalogue de produits → + Ajouter un produit** (`/test/products`).

Crée **3 produits**, chacun avec **2 prix récurrents** (mensuel + annuel),
**devise CHF**. Laisse le **comportement fiscal par défaut** : tant que tu n'es
pas assujetti à la TVA (Étape 4), tes prix sont **nets, sans TVA** :

| Produit | Prix mensuel | Prix annuel (2 mois offerts) |
|---|---|---|
| **Solo** | 690 CHF / mois | 6 900 CHF / an |
| **Bureau** | 2 400 CHF / mois | 24 000 CHF / an |
| **Enterprise** | 4 900 CHF / mois | 49 000 CHF / an |

Pour chaque produit :
1. Nom = `Solo` (puis `Bureau`, puis `Enterprise`).
2. Modèle tarifaire = **Standard**, **Récurrent**.
3. Ajoute le prix **mensuel** : montant, CHF, période **mensuelle**.
4. **Ajoute un autre prix** sur le même produit : montant annuel, CHF,
   période **annuelle**.
5. Enregistre, puis **copie les deux `price_…`** (clique sur chaque prix, l'ID
   commence par `price_`).

Reporte les 6 IDs dans le tableau de l'aperçu (colonne « Contenu »).

> Astuce : nomme tes prix « Solo mensuel » / « Solo annuel » dans Stripe pour
> t'y retrouver. L'ID `price_…` est ce qui compte pour le code.

---

## Étape 4 — TVA suisse — PLUS TARD (pas maintenant)

⚠️ En Suisse, tu n'es **assujetti à la TVA qu'au-dessus de 100 000 CHF de
chiffre d'affaires par an**. En dessous, tu **ne factures pas de TVA** (et tu
n'as pas le droit de la collecter sans être enregistré). **Donc : ne fais rien
ici pour l'instant.** Tes prix sont nets (690 / 2 400 / 4 900 CHF).

Le jour où tu franchis 100 000 CHF/an :

1. Inscris-toi à la TVA auprès de l'AFC et obtiens ton n° TVA (IDE).
2. Menu **Plus → Tax** (Stripe Tax) → **Activer**, adresse + n° TVA, Suisse en
   juridiction de collecte.
3. Passe chaque **prix** en comportement fiscal **« hors taxes »** (exclusive).
4. Côté app : réaffiche « HT · TVA 8.1 % » (voir note dans le récap ci-dessous).

> Tu devras aussi t'annoncer comme **indépendant à l'AVS** dès que l'activité
> est régulière (démarche sociale, sans rapport avec Stripe).

---

## Étape 5 — Configurer le webhook

C'est ce qui permet à LESO d'**activer le plan** dès qu'un paiement réussit.

1. Menu **Développeurs → Webhooks → + Ajouter un endpoint** (`/test/webhooks`).
2. **URL du endpoint** :
   ```
   https://TON-API.onrender.com/api/billing/webhook
   ```
   Remplace `TON-API.onrender.com` par l'URL de ton service API Render
   (= ta variable `BACKEND_URL`).
3. **Événements à écouter** — sélectionne exactement ces 5 :
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
4. Crée l'endpoint, puis clique **« Révéler »** sur le **Secret de signature**
   (`whsec_…`) → ce sera `STRIPE_WEBHOOK_SECRET`.

---

## Étape 6 — Renseigner les variables sur Render

1. Render → service **bet-agent-api** → onglet **Environment**.
2. Renseigne les 8 variables Stripe (valeurs des étapes 2, 3, 5).
3. Ajoute/règle **`BETA_MODE` = `false`** pour débloquer les boutons de paiement.
   *(Tant que `BETA_MODE` est absent ou `true`, le front affiche « paiement en
   cours de déploiement » — utile si tu veux préparer Stripe sans encore
   l'ouvrir aux clients.)*
4. Render redéploie automatiquement.

> Les mêmes `STRIPE_PRICE_*` figurent aussi sur le service **bet-agent-worker** :
> tu peux les y laisser vides, le worker ne crée pas de paiement.

---

## Étape 7 — Tester (mode Test)

1. Connecte-toi à LESO → **Facturation**.
2. Choisis l'intervalle **Mensuel** ou **Annuel**, clique **Choisir ce plan**.
3. Sur la page Stripe, paie avec la **carte de test** :
   ```
   Numéro : 4242 4242 4242 4242
   Date   : n'importe quelle date future   CVC : n'importe quel 3 chiffres
   ```
4. Après paiement, tu dois être redirigé vers `…/billing?success=1` et le plan
   doit passer à **Solo/Bureau/Enterprise** (l'activation se fait via le webhook).
5. Vérifie dans **Stripe → Développeurs → Webhooks → ton endpoint** que
   l'événement `checkout.session.completed` est **« Réussi » (200)**.

**Cartes de test utiles** :
- Paiement refusé : `4000 0000 0000 0002`
- Authentification 3D Secure : `4000 0027 6000 3184`
- Échec de paiement récurrent (pour tester la suspension) : voir docs Stripe.

Si le webhook échoue (≠ 200) : vérifie l'URL et que `STRIPE_WEBHOOK_SECRET`
correspond bien à CE endpoint.

---

## Étape 8 — Passer en Live

Quand tout marche en Test :

1. Bascule le dashboard en **Mode Live** (toggle en haut à droite).
2. **Active ton compte** : Stripe demande tes infos d'entreprise + IBAN pour les
   virements (KYC). Obligatoire pour encaisser réellement.
3. **Refais les étapes 2, 3, 5 en Live** (clés `sk_live_…`, produits/prix Live,
   webhook Live avec un nouveau `whsec_…`). Les objets Test ne sont pas copiés.
4. Remplace les 8 variables Render par les valeurs **Live**.
5. Fais un vrai achat-test avec ta propre carte (puis rembourse-toi depuis Stripe
   si besoin).

---

## Réactiver l'affichage TVA dans l'app (le moment venu)

Quand tu seras assujetti, rebascule l'affichage « HT · TVA 8.1 % » :
- `frontend/src/app/page.tsx` : la note sous les tarifs + l'unité « CHF / mois ».
- `frontend/src/app/(dashboard)/billing/page.tsx` : l'unité de prix + la note
  « Prix nets · TVA non applicable ».
- `frontend/src/app/(auth)/register/page.tsx` : la ligne du plan.

C'est uniquement du texte (aucune logique de calcul) ; Stripe Tax s'occupe du
montant réel de la TVA au paiement.

---

## Checklist finale

- [ ] `sk_…` (secret) renseignée
- [ ] 3 produits Solo / Bureau / Enterprise créés
- [ ] 6 prix (mensuel + annuel) créés, 6 `price_…` copiés
- [ ] ~~Stripe Tax / TVA~~ → **plus tard** (dès 100 000 CHF/an, cf. Étape 4)
- [ ] Webhook créé sur `…/api/billing/webhook` avec les 5 événements
- [ ] `whsec_…` renseigné
- [ ] 8 variables Stripe sur Render
- [ ] `BETA_MODE=false`
- [ ] Test carte 4242 → plan activé + webhook 200
- [ ] (au lancement) tout refait en Live + compte activé (KYC)

---

## Dépannage rapide

| Symptôme | Cause probable |
|---|---|
| Boutons « Bientôt disponible » grisés | `BETA_MODE` encore à `true` |
| « La facturation annuelle n'est pas disponible » | `STRIPE_PRICE_*_YEARLY` vide |
| Paiement OK mais plan pas activé | Webhook absent / mauvaise URL / mauvais `whsec_` |
| Webhook en erreur 400 « Signature invalide » | `STRIPE_WEBHOOK_SECRET` ne correspond pas à cet endpoint |
| `Plan inconnu` au checkout | `STRIPE_PRICE_*` (mensuel) vide ou mal copié |
