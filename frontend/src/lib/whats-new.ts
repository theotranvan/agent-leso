// Journal des nouveautés affiché aux utilisateurs à la reconnexion.
//
// Pour annoncer une mise à jour : ajoutez une entrée EN HAUT de la liste avec un
// nouvel `id` (la date suffit). Les utilisateurs qui ne l'ont pas encore vue auront
// le pop-up à leur prochaine connexion. Rédigez en langage métier (ingénieur),
// pas en jargon technique, et gardez l'essentiel.

export type WhatsNewEntry = {
  id: string;       // identifiant unique (sert à savoir si l'utilisateur l'a déjà vue)
  date: string;     // libellé affiché (ex. "Juin 2026")
  title: string;    // titre court de la mise à jour
  items: string[];  // nouveautés essentielles, une phrase chacune
};

// Les plus récentes EN PREMIER.
export const WHATS_NEW: WhatsNewEntry[] = [
  {
    id: '2026-06-06',
    date: 'Juin 2026',
    title: 'Thermique, IDC et livrables plus complets',
    items: [
      'Thermique SIA 380/1 : vous saisissez désormais la SRE, les installations techniques (chauffage, ventilation, eau chaude) et une désignation libre pour chaque paroi et fenêtre — avec un catalogue réutilisable d’un projet à l’autre. La fiche de saisie Lesosai est fournie en PDF prête à l’emploi.',
      'IDC Genève : l’indice est maintenant corrigé du climat (DJU de l’année), l’affectation du bâtiment est sélectionnable pour appliquer les bons seuils OCEN, et les valeurs lues sur les factures sont corrigeables avant le calcul.',
      'Générer un livrable : la liste est réorganisée du plus courant au plus spécialisé, et un bouton d’aide explique chaque livrable (à quoi il sert, prérequis, points à savoir).',
      'Comptes-rendus et notes de calcul : référentiel normatif correct selon le pays (SIA en Suisse) et résumé de document désormais fourni en PDF.',
    ],
  },
];
