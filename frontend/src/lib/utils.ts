import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string | Date): string {
  const d = typeof iso === 'string' ? new Date(iso) : iso;
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function formatDateTime(iso: string | Date): string {
  const d = typeof iso === 'string' ? new Date(iso) : iso;
  return d.toLocaleString('fr-FR', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function formatCurrency(n: number, currency = 'EUR'): string {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency }).format(n);
}

export const TASK_TYPE_LABELS: Record<string, string> = {
  redaction_cctp: 'Rédaction CCTP',
  note_calcul_structure: 'Note de calcul structure',
  verification_eurocode: 'Vérification Eurocode',
  calcul_thermique_re2020: 'Calcul thermique RE2020',
  calcul_acoustique: 'Calcul acoustique',
  chiffrage_dpgf: 'Chiffrage DPGF',
  chiffrage_dqe: 'Chiffrage DQE',
  coordination_inter_lots: 'Coordination inter-lots',
  memoire_technique: 'Mémoire technique',
  compte_rendu_reunion: 'Compte-rendu réunion',
  doe_compilation: 'Compilation DOE',
  dossier_permis_construire: 'Dossier permis de construire',
  analyse_ifc: 'Analyse IFC',
  resume_document: 'Résumé de document',
  veille_reglementaire: 'Veille réglementaire',
  alerte_norme: 'Alerte norme',
  email_notification: 'Notification email',
  extraction_metadata: 'Extraction métadonnées',
};

export const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: 'En attente', color: 'bg-slate-100 text-slate-700' },
  running: { label: 'En cours', color: 'bg-blue-100 text-blue-700' },
  completed: { label: 'Terminée', color: 'bg-emerald-100 text-emerald-700' },
  failed: { label: 'Échouée', color: 'bg-red-100 text-red-700' },
};

export const LOT_LABELS: Record<string, string> = {
  electricite: 'Électricité',
  cvc: 'CVC',
  structure: 'Structure',
  facade: 'Façade',
  plomberie: 'Plomberie',
  gros_oeuvre: 'Gros œuvre',
  second_oeuvre: 'Second œuvre',
  vrd: 'VRD',
  acoustique: 'Acoustique',
  thermique: 'Thermique',
};
