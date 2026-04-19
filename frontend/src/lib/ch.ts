// Constantes Suisse pour le frontend

export const CANTONS_ROMANDS = [
  { code: 'GE', name: 'Genève' },
  { code: 'VD', name: 'Vaud' },
  { code: 'NE', name: 'Neuchâtel' },
  { code: 'FR', name: 'Fribourg' },
  { code: 'VS', name: 'Valais' },
  { code: 'JU', name: 'Jura' },
];

export const CANTONS_AUTRES = [
  { code: 'BE', name: 'Berne' },
  { code: 'ZH', name: 'Zurich' },
  { code: 'BS', name: 'Bâle-Ville' },
  { code: 'BL', name: 'Bâle-Campagne' },
  { code: 'AG', name: 'Argovie' },
  { code: 'SO', name: 'Soleure' },
  { code: 'LU', name: 'Lucerne' },
  { code: 'SG', name: 'Saint-Gall' },
  { code: 'TI', name: 'Tessin' },
  { code: 'TG', name: 'Thurgovie' },
  { code: 'GR', name: 'Grisons' },
];

export const TOUS_CANTONS = [...CANTONS_ROMANDS, ...CANTONS_AUTRES];

export const AFFECTATIONS_SIA = [
  { value: 'logement_individuel', label: 'Habitation individuelle' },
  { value: 'logement_collectif', label: 'Habitation collective' },
  { value: 'administration', label: 'Administration / bureau' },
  { value: 'ecole', label: 'École' },
  { value: 'commerce', label: 'Commerce' },
  { value: 'restauration', label: 'Restauration' },
  { value: 'lieu_rassemblement', label: 'Lieu de rassemblement' },
  { value: 'hopital', label: 'Hôpital' },
  { value: 'industriel', label: 'Industrie' },
  { value: 'depot', label: 'Dépôt' },
  { value: 'sport', label: 'Installation sportive' },
];

export const OPERATION_TYPES = [
  { value: 'neuf', label: 'Construction neuve' },
  { value: 'renovation', label: 'Rénovation' },
  { value: 'transformation', label: 'Transformation' },
  { value: 'surelevation', label: 'Surélévation' },
];

export const STANDARDS_ENERGETIQUES = [
  { value: 'sia_380_1', label: 'SIA 380/1 (minimum légal)' },
  { value: 'cecb', label: 'CECB' },
  { value: 'cecb_plus', label: 'CECB Plus' },
  { value: 'minergie', label: 'MINERGIE' },
  { value: 'minergie_p', label: 'MINERGIE-P' },
  { value: 'minergie_a', label: 'MINERGIE-A' },
];

export const VECTEURS_ENERGETIQUES = [
  { value: 'gaz', label: 'Gaz naturel', unit: 'm³' },
  { value: 'mazout', label: 'Mazout', unit: 'litres' },
  { value: 'chauffage_distance', label: 'Chauffage à distance (CAD)', unit: 'kWh' },
  { value: 'pac_air_eau', label: 'PAC air-eau', unit: 'kWh' },
  { value: 'pac_sol_eau', label: 'PAC sol-eau', unit: 'kWh' },
  { value: 'pellet', label: 'Pellets (granulés bois)', unit: 'kg' },
  { value: 'buche', label: 'Bûches bois', unit: 'stères' },
  { value: 'electrique', label: 'Électrique direct', unit: 'kWh' },
  { value: 'solaire_thermique', label: 'Solaire thermique', unit: 'kWh' },
];

export const AEAI_BUILDING_TYPES = [
  { value: 'habitation_faible', label: 'Habitation < 11 m' },
  { value: 'habitation_moyenne', label: 'Habitation 11-30 m' },
  { value: 'habitation_elevee', label: 'Habitation > 30 m' },
  { value: 'administration_faible', label: 'Administration basse' },
  { value: 'administration_moyenne', label: 'Administration moyenne' },
  { value: 'administration_elevee', label: 'Administration haute' },
  { value: 'ecole', label: 'École / enseignement' },
  { value: 'erp_petit', label: 'Lieu de rassemblement ≤ 300 pers.' },
  { value: 'erp_moyen', label: '300-1000 pers.' },
  { value: 'erp_grand', label: '> 1000 pers.' },
  { value: 'parking_souterrain', label: 'Parking souterrain' },
  { value: 'industriel', label: 'Bâtiment industriel' },
  { value: 'depot', label: 'Dépôt' },
  { value: 'hopital', label: 'Hôpital / EMS' },
];

export const VAT_RATES_CH = [
  { value: 8.1, label: '8.1% standard' },
  { value: 2.6, label: '2.6% taux réduit' },
  { value: 3.8, label: '3.8% hébergement' },
  { value: 0.0, label: '0% exempt' },
];

export const PHASES_SIA = [
  { value: '11', label: '11 - Définition des objectifs' },
  { value: '21', label: '21 - Études préliminaires' },
  { value: '31', label: '31 - Avant-projet' },
  { value: '32', label: '32 - Projet de l\'ouvrage' },
  { value: '33', label: '33 - Demande d\'autorisation' },
  { value: '41', label: '41 - Appel d\'offres' },
  { value: '51', label: '51 - Projet d\'exécution' },
  { value: '52', label: '52 - Exécution' },
  { value: '53', label: '53 - Mise en service' },
];

export function formatCHF(n: number): string {
  return new Intl.NumberFormat('fr-CH', { style: 'currency', currency: 'CHF' }).format(n);
}

export function formatCHDate(d: string | Date): string {
  const date = typeof d === 'string' ? new Date(d) : d;
  return date.toLocaleDateString('fr-CH', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

export function validateCheVat(v: string): boolean {
  // Format CHE-123.456.789 ou CHE-123.456.789 MWST/TVA
  return /^CHE-?\d{3}\.?\d{3}\.?\d{3}(\s?(MWST|TVA|IVA))?$/i.test(v.trim());
}

export const STATUS_COLORS: Record<string, string> = {
  OK: 'bg-emerald-100 text-emerald-700',
  CONFORME: 'bg-emerald-100 text-emerald-700',
  ATTENTION: 'bg-amber-100 text-amber-700',
  A_VERIFIER: 'bg-slate-100 text-slate-700',
  ALERTE: 'bg-orange-100 text-orange-700',
  CRITIQUE: 'bg-red-100 text-red-700',
  NON_CONFORME: 'bg-red-100 text-red-700',
  NON_APPLICABLE: 'bg-slate-50 text-slate-500',
  INFO: 'bg-blue-100 text-blue-700',
  IMPORTANT: 'bg-amber-100 text-amber-700',
  BLOQUANT: 'bg-red-100 text-red-700',
};
