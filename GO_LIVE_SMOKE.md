# Smoke test prod — générer 1 de chaque livrable

Objectif : confirmer en conditions réelles (env prod + vrai LLM + PDF/Excel) que
chaque livrable aboutit. Le code est testé (320 tests), il reste à valider
l'environnement live et la qualité du rendu.

À faire sur **https://digitran.ch**, connecté. Pour chaque ligne : lancer, attendre
la fin (statut **Terminé / À valider**), ouvrir le fichier, vérifier le critère.

> Astuce : crée d'abord **un projet** (canton VD ou GE, affectation logement
> collectif, une adresse) — plusieurs livrables s'y rattachent.

## Priorité 1 — les plus utilisés (fais ceux-là en premier)

| # | Livrable | Où / inputs minimaux | ✅ Critère de réussite |
|---|----------|----------------------|------------------------|
| 1 | **Simulation énergétique** | Générer un livrable → Simulation. SRE 1000, logement collectif, GE, SIA 380/1 neuf, gaz, compact | PDF s'ouvre ; **Qh ≈ 43–44 kWh/m²·an**, classe affichée, « conforme » |
| 2 | **CCTP** | Générer → CCTP. Lot **Chauffage**, niveau **standard**, surface 500, une contrainte | PDF CCTP : articles CFC 23x, **normes SIA citées**, à ta charte |
| 3 | **Chiffrage DPGF** | Générer → DPGF. Lot **Chauffage**, niveau **standard**, surface 500 | **Excel** + PDF récap ; total en **CHF** (pas €), fourchette affichée |
| 4 | **Compte-rendu** | Générer → Compte-rendu. Intitulé, **date**, **lieu**, 2 participants, notes | PDF CR : objet/date/lieu/participants corrects, tableau d'actions |

## Priorité 2 — modules métier

| # | Livrable | Où / inputs minimaux | ✅ Critère |
|---|----------|----------------------|-----------|
| 5 | **Thermique SIA 380/1** | Module **Thermique SIA** → nouveau modèle (zones, parois, U-values) | Justificatif PDF, Qh/Ep cohérents |
| 6 | **Structure SIA 260** | Module **Structure SIA** → modèle (nœuds, barres, charges) | Note de calcul, double-check M=qL²/8 |
| 7 | **IDC Genève** | Module **IDC Genève** → bâtiment (SRE, vecteur) + 1 conso ou facture | Rapport + formulaire OCEN, IDC en kWh/m²·an |
| 8 | **AEAI checklist** | Générer → AEAI. Type habitation moyenne, hauteur 18 | Checklist par catégories, points pertinents |
| 9 | **Métrés IFC** | Module **Métrés IFC** → uploader un IFC | Tableau surfaces SIA 416 + DPGF par CFC |
| 10 | **Coordination** | Générer → Coordination. Uploader **2 IFC** (2 lots) | Rapport de conflits (BCF), matrice par couple de lots |

## Priorité 3 — autres

| # | Livrable | Inputs | ✅ Critère |
|---|----------|--------|-----------|
| 11 | **DQE** | Lot + surface | Excel multi-lots, total CHF |
| 12 | **Mémoire technique** | Brief AO | PDF argumenté |
| 13 | **Dossier mise à l'enquête** | Projet (canton, affectation, SRE) + spécificités | Mémoire multi-domaines |
| 14 | **Réponse aux observations** | PDF courrier + **autorité** (DALE/DGT…) | Réponse point par point |
| 15 | **Contrôle réglementaire GE** | Projet GE | Rapport de conformité |
| 16 | **Résumé de document** | Uploader un PDF | Résumé PDF |
| 17 | **Veille romande** | — | Synthèse (peut dépendre des sources) |

## Que vérifier à chaque fois

- [ ] La tâche passe en **Terminé / À valider** (pas « Échec »).
- [ ] Le **PDF/Excel s'ouvre** sans corruption.
- [ ] L'export **Word** fonctionne aussi (bouton Word sur la tâche).
- [ ] Les **valeurs chiffrées** sont plausibles ; devise **CHF**.
- [ ] Les **normes SIA / CFC** apparaissent là où attendu.

## Si un livrable échoue

Note : (a) le **type** de livrable, (b) le **message d'erreur** affiché, et
si possible (c) le **statut du webhook/logs Render** au même moment.
→ Envoie-moi ces 3 infos et je corrige (la plupart des échecs prod restants
seraient : dépendance système PDF manquante, colonne DB absente, ou quota LLM).

---

**Conseil** : fais d'abord la **Priorité 1** (4 livrables, ~5 min). Si ces 4
aboutissent proprement, tu peux démarcher tes premiers clients en confiance ;
les autres se valident au fil de l'eau.
