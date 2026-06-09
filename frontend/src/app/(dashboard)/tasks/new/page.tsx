'use client';
import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, ArrowRight, Loader2, FileText, Flame, Building, Building2, Shield, Bell,
  Layers, FileCheck2, MessageSquareWarning, Ruler, Zap, Users, Calculator, BookOpen,
  PenTool, ScrollText, HelpCircle, X, Library, Bookmark, Trash2,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Banner } from '@/components/ui/banner';
import { Dropzone } from '@/components/ui/dropzone';
import { CANTONS_ROMANDS, AFFECTATIONS_SIA } from '@/lib/ch';
import { useActiveProject } from '@/lib/active-project';

type TaskHelp = {
  what: string;        // à quoi sert le livrable
  prereq: string;      // prérequis / ce qu'il faut sous la main
  tips?: string;       // petites choses à savoir
};

type TaskCategory = {
  id: string;
  title: string;
  description: string;
  icon: any;
  color: string;
  fields: string[];  // champs du form à afficher
  days_saved?: string;
  help?: TaskHelp;
};

// Ordre = fréquence d'usage réelle en bureau (du plus utilisé au plus spécialisé).
// Modifier l'ordre ici suffit à réorganiser la page "Générer un livrable".
const TASK_CATEGORIES: TaskCategory[] = [
  // ----- Cœur quotidien : rédaction & livrables réglementaires fréquents -----
  {
    id: 'redaction_cctp',
    title: 'CCTP',
    description: 'Descriptif des prestations par lot — rédigé selon SIA 451',
    icon: ScrollText, color: 'bg-blue-50 text-blue-700',
    fields: ['project_name', 'lot', 'type_ouvrage', 'niveau_prestation', 'surface', 'articles_libres', 'contraintes'],
    help: {
      what: 'Rédige le cahier des charges techniques d\'un lot : prescriptions, description du matériel, exigences de performance, contrôles et réceptions.',
      prereq: 'Le lot concerné, le type d\'ouvrage et le niveau de prestation visé.',
      tips: 'Lot absent de la liste ? Choisissez « Autre lot » et décrivez-le. Le champ « Articles sur mesure » accepte n\'importe quelle prescription : LESO l\'intègre telle quelle. Le résultat est éditable (PDF + Word) avant diffusion.',
    },
  },
  {
    id: 'justificatif_sia_380_1',
    title: 'Justificatif SIA 380/1',
    description: 'Thermique — requiert un modèle ou un IFC (redirige vers le module)',
    icon: Flame, color: 'bg-orange-50 text-orange-700',
    fields: ['redirect_thermique'],
    help: {
      what: 'Justificatif thermique officiel SIA 380/1. Ouvre le module Thermique : saisie de la composition (zones, parois, ouvertures) puis export/import Lesosai.',
      prereq: 'La composition de l\'enveloppe : surfaces et valeurs U des parois, fenêtres. Les métrés IFC fournissent les surfaces.',
      tips: 'Pensez à « Enregistrer la composition » avant de lancer l\'export. Un calcul indicatif rapide est aussi disponible en avant-projet.',
    },
  },
  {
    id: 'dossier_mise_enquete',
    title: 'Dossier mise en enquête',
    description: 'Mémoire justificatif APA/APC avec tableau SIA 416 et checklist des pièces à fournir',
    icon: FileCheck2, color: 'bg-purple-50 text-purple-700',
    days_saved: '5-10 j économisés',
    fields: ['project_name', 'canton', 'address', 'affectation', 'operation_type', 'sre_m2', 'specificities', 'author'],
    help: {
      what: 'Rédige le mémoire justificatif de demande d\'autorisation (APA/APC) : descriptif de l\'ouvrage, tableau de surfaces SIA 416 et liste des pièces à joindre.',
      prereq: 'Caractéristiques du projet : canton, adresse, affectation, type d\'opération et SRE (m²). Les métrés IFC fournissent ces chiffres.',
      tips: 'Renseignez les « spécificités » (parking, toiture végétalisée…) pour enrichir le descriptif. À relire et signer avant dépôt.',
    },
  },
  {
    id: 'metres_automatiques_ifc',
    title: 'Métrés automatiques IFC',
    description: 'Extrait SRE, volumes et quantités par CFC depuis un IFC. Produit un DPGF pré-rempli.',
    icon: Ruler, color: 'bg-amber-50 text-amber-700',
    days_saved: '1-2 j économisés',
    fields: ['project_name', 'ifc_upload', 'author'],
    help: {
      what: 'Lit une maquette IFC et calcule automatiquement surfaces (SRE), volumes, enveloppe et quantités par CFC. Produit aussi un bordereau DPGF pré-rempli.',
      prereq: 'Un fichier IFC de la maquette architecte (max 50 Mo).',
      tips: 'Exportez l\'IFC AVEC les quantités : Revit « Export IFC quantities », ArchiCAD « Compute IFC quantities ». Sans cette case, tous les chiffres sortent à zéro.',
    },
  },
  {
    id: 'releve_thermique_2d',
    title: 'Relevé thermique (plans 2D)',
    description: 'Extrait SRE, toiture, façades & fenêtres par orientation, planchers et ponts thermiques depuis des plans PDF — sans maquette 3D.',
    icon: Flame, color: 'bg-orange-50 text-orange-700',
    days_saved: 'relevé Lesosai automatisé',
    fields: ['project_name', 'canton', 'plan_multi_upload', 'author'],
    help: {
      what: 'Pour les bilans thermiques Lesosai en phase 3.3, sans IFC : LESO lit vos plans 2D (façades, étages, toiture, coupes) et relève les surfaces (SRE, toiture, façades et fenêtres par orientation, planchers, ponts thermiques).',
      prereq: 'Vos plans en PDF ou images : les 4 façades (avec leur orientation dans le titre), les plans d\'étage, la toiture et les coupes.',
      tips: 'Chaque valeur est relevée par lecture des cotes et annotations, avec un niveau de confiance. À VÉRIFIER et valider par le thermicien avant saisie Lesosai.',
    },
  },
  {
    id: 'chiffrage_dpgf',
    title: 'DPGF / Chiffrage',
    description: 'Devis quantitatif structuré par lot à partir du programme',
    icon: Calculator, color: 'bg-emerald-50 text-emerald-700',
    fields: ['project_name', 'lot', 'niveau_prestation', 'surface', 'notes'],
    help: {
      what: 'Génère un bordereau DPGF par lot avec postes, unités et prix unitaires indicatifs (indice 2025, ajusté au canton).',
      prereq: 'Le lot et la surface concernée (ou un métré collé dans les notes).',
      tips: 'Les prix sont indicatifs : à ajuster selon vos sous-traitants et le marché.',
    },
  },
  {
    id: 'controle_reglementaire_geneve',
    title: 'Contrôle réglementaire',
    description: 'Rapport pré-dépôt : zone, énergie, LDTR, AEAI, stationnement',
    icon: FileText, color: 'bg-blue-50 text-blue-700',
    fields: ['project_name', 'canton', 'address', 'affectation', 'operation_type', 'sre_m2', 'nb_logements'],
    help: {
      what: 'Vérification automatique avant dépôt : indices d\'utilisation du sol, énergie, LDTR, AEAI, stationnement. Produit un rapport vert/rouge par critère.',
      prereq: 'Canton, adresse, affectation, type d\'opération, SRE et nombre de logements.',
      tips: 'Filet de sécurité avant dépôt — ce n\'est pas un avis juridique. Idéal pour repérer un point bloquant tôt.',
    },
  },
  {
    id: 'aeai_checklist_generation',
    title: 'Checklist AEAI',
    description: 'Checklist incendie pour une typologie donnée',
    icon: Shield, color: 'bg-amber-50 text-amber-700',
    fields: ['project_name', 'building_type', 'height_m', 'nb_occupants_max', 'special_context'],
    help: {
      what: 'Génère la checklist de conformité incendie AEAI adaptée à la typologie du bâtiment, avec les références des directives.',
      prereq: 'La typologie, la hauteur et l\'occupation maximale du bâtiment.',
      tips: 'Décrivez le « contexte particulier » (parking, local déchets, vélos…) : LESO ajoute les points de vigilance correspondants et l\'autorité cantonale compétente.',
    },
  },
  {
    id: 'idc_geneve_rapport',
    title: 'IDC Genève',
    description: 'Extraction factures, calcul, formulaire OCEN (redirige vers le module)',
    icon: Building2, color: 'bg-emerald-50 text-emerald-700',
    fields: ['redirect_idc'],
    help: {
      what: 'Calcule l\'indice de dépense de chaleur (IDC) genevois et produit le rapport annuel + le formulaire OCEN, à partir des consommations.',
      prereq: 'EGID, SRE, énergie de chauffage et consommations des 3 dernières années (factures).',
      tips: 'Obligatoire chaque année pour les bâtiments chauffés à Genève. Le module peut extraire les m³/kWh d\'une facture PDF.',
    },
  },
  {
    id: 'reponse_observations_autorite',
    title: 'Réponse aux observations',
    description: 'Lettre argumentée point par point depuis un courrier DALE, DGT ou CAMAC',
    icon: MessageSquareWarning, color: 'bg-red-50 text-red-700',
    days_saved: '1-3 j économisés',
    fields: ['project_name', 'canton', 'authority', 'autorite_pdf_upload', 'author'],
    help: {
      what: 'Lit le courrier d\'observations d\'une autorité et rédige une réponse structurée, point par point, prête à renvoyer.',
      prereq: 'Le PDF du courrier de l\'autorité (DALE, DGT, CAMAC…) + le canton.',
      tips: 'Relisez chaque réponse : l\'argumentaire est un projet à valider par l\'ingénieur responsable.',
    },
  },
  {
    id: 'compte_rendu_reunion',
    title: 'Compte-rendu de réunion',
    description: 'Résumé structuré depuis des notes ou un enregistrement de réunion',
    icon: Users, color: 'bg-slate-50 text-slate-700',
    fields: ['project_name', 'meeting_title', 'meeting_date', 'meeting_heure', 'meeting_lieu', 'participants', 'notes'],
    help: {
      what: 'Transforme des notes brutes en compte-rendu structuré : décisions, actions, délais, présents.',
      prereq: 'Vos notes de réunion (texte) et la liste des participants.',
      tips: 'Séparez les participants par des virgules. Plus les notes sont précises, meilleur est le CR.',
    },
  },
  {
    id: 'resume_document',
    title: 'Résumé de document',
    description: 'Synthèse claire d\'un PDF technique (rapport, norme, étude)',
    icon: ScrollText, color: 'bg-slate-50 text-slate-700',
    fields: ['project_name', 'document_upload'],
    help: {
      what: 'Produit un résumé structuré d\'un document PDF : points clés, conclusions, points de vigilance.',
      prereq: 'Le document PDF à résumer (rapport de sol, norme, notice, étude…).',
      tips: 'Idéal pour dégrossir un rapport long. À relire : le résumé ne remplace pas la lecture du document source.',
    },
  },
  // ----- Situationnel : avant-projet, appels d'offres, suivi de chantier -----
  {
    id: 'simulation_energetique_rapide',
    title: 'Simulation énergétique rapide',
    description: 'Estime Qh en 30 s depuis un programme — avant-projet ou concours, sans IFC',
    icon: Zap, color: 'bg-orange-50 text-orange-700',
    fields: ['project_name', 'canton', 'affectation', 'sre_m2', 'standard', 'heating_vector', 'facteur_forme'],
    help: {
      what: 'Estime le besoin de chaleur Qh d\'un bâtiment en 30 secondes à partir du programme, sans IFC ni saisie détaillée. Utile en concours ou pour comparer des variantes.',
      prereq: 'Canton, affectation, SRE (m²), standard énergétique et vecteur de chauffage.',
      tips: 'Résultat INDICATIF (avant-projet). Le justificatif officiel SIA 380/1 se fait dans le module Thermique avec Lesosai.',
    },
  },
  {
    id: 'memoire_technique',
    title: 'Mémoire technique',
    description: 'Note méthodologique convaincante pour une réponse à appel d\'offres',
    icon: BookOpen, color: 'bg-indigo-50 text-indigo-700',
    fields: ['project_name', 'brief', 'author'],
    help: {
      what: 'Rédige un mémoire technique argumenté pour une réponse à appel d\'offres : méthodologie, moyens, organisation.',
      prereq: 'Le brief ou le CCTP du client (collé dans le champ prévu).',
      tips: 'Plus le brief est complet, plus le mémoire est ciblé sur les critères de notation.',
    },
  },
  {
    id: 'chiffrage_dqe',
    title: 'DQE',
    description: 'Devis quantitatif estimatif structuré par lot, avec prix unitaires',
    icon: Calculator, color: 'bg-emerald-50 text-emerald-700',
    fields: ['project_name', 'lot', 'niveau_prestation', 'surface', 'notes'],
    help: {
      what: 'Devis quantitatif estimatif détaillé par lot, avec quantités et prix unitaires indicatifs.',
      prereq: 'Le lot et la surface concernée (ou un métré collé dans les notes).',
      tips: 'Comme le DPGF, les prix sont indicatifs et à ajuster au marché.',
    },
  },
  {
    id: 'rapport_chantier',
    title: 'Rapport de chantier',
    description: 'Compte-rendu de visite depuis des notes de terrain',
    icon: PenTool, color: 'bg-amber-50 text-amber-700',
    fields: ['project_name', 'notes', 'author'],
    help: {
      what: 'Met en forme un rapport de visite de chantier : constatations, réserves, suites à donner.',
      prereq: 'Vos notes de terrain (texte). Le nom du projet.',
      tips: 'Restez factuel dans les notes : le rapport reprend vos constats, à valider avant diffusion.',
    },
  },
  // ----- Spécialisé : ingénierie structure & coordination BIM -----
  {
    id: 'note_calcul_sia_260_267',
    title: 'Note structure SIA 260-267',
    description: 'SAF pour Scia/RFEM puis note de calcul (redirige vers le module)',
    icon: Building, color: 'bg-slate-50 text-slate-700',
    fields: ['redirect_structure'],
    help: {
      what: 'Génère un fichier SAF (géométrie + combinaisons SIA 260) pour Scia/RFEM, puis — après import de vos résultats — un double-check analytique et la note de calcul SIA 260-267.',
      prereq: 'La trame du bâtiment (niveaux, entraxes, sections) saisie dans le module, ou un IFC structure.',
      tips: 'La note finale n\'est générée qu\'après votre validation explicite d\'ingénieur. Le calcul de résistance reste fait dans votre logiciel.',
    },
  },
  {
    id: 'coordination_inter_lots',
    title: 'Coordination inter-lots',
    description: 'Pré-détection des conflits entre maquettes IFC (par enveloppe / bounding box) sur différents lots. Rapport + BCF à confirmer en géométrie fine.',
    icon: Layers, color: 'bg-indigo-50 text-indigo-700',
    days_saved: '2-4 j économisés',
    fields: ['project_name', 'ifc_multi_upload', 'author'],
    help: {
      what: 'Compare plusieurs maquettes IFC (un lot chacune) et pré-détecte les collisions par recouvrement d\'enveloppes (bounding box). Produit un rapport et un fichier BCF ouvrable dans vos outils BIM, à confirmer en géométrie fine.',
      prereq: 'Au moins 2 maquettes IFC, une par lot (structure, CVC, sanitaire…), avec le nom du lot indiqué.',
      tips: 'Plus les maquettes sont géoréférencées au même point de base, plus la détection est fiable.',
    },
  },
];

const MODULE_REDIRECTS: Record<string, string> = {
  redirect_thermique: '/thermique',
  redirect_structure: '/structure',
  redirect_idc: '/idc',
};

export default function NewTaskPage() {
  return (
    <Suspense fallback={<div className="text-muted-foreground">Chargement…</div>}>
      <NewTaskInner />
    </Suspense>
  );
}

function NewTaskInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { activeProject } = useActiveProject();

  const preselectedType = searchParams.get('type');
  const preselectedProject = searchParams.get('project_id') || searchParams.get('project');

  const [selected, setSelected] = useState<TaskCategory | null>(
    preselectedType ? TASK_CATEGORIES.find((c) => c.id === preselectedType) || null : null
  );
  const [projectId, setProjectId] = useState<string>(preselectedProject || activeProject?.id || '');
  const [projects, setProjects] = useState<any[]>([]);
  const [form, setForm] = useState<any>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedDocId, setUploadedDocId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string>('');
  const [openHelp, setOpenHelp] = useState<string | null>(null);

  useEffect(() => {
    api.projects.list().then((r: any) => setProjects(r.projects || [])).catch(() => {});
  }, []);

  // Sync avec projet actif
  useEffect(() => {
    if (!projectId && activeProject?.id) setProjectId(activeProject.id);
  }, [activeProject, projectId]);

  // Pré-remplit canton/affectation depuis le projet actif (adapte au canton)
  useEffect(() => {
    if (!activeProject) return;
    setForm((f: any) => ({
      ...f,
      canton: f.canton ?? activeProject.canton ?? undefined,
      affectation: f.affectation ?? activeProject.affectation ?? undefined,
    }));
  }, [activeProject]);

  // Redirect si l'utilisateur choisit un module
  useEffect(() => {
    if (!selected) return;
    const redirect = selected.fields.find((f) => f.startsWith('redirect_'));
    if (redirect && MODULE_REDIRECTS[redirect]) {
      router.push(MODULE_REDIRECTS[redirect]);
    }
  }, [selected, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    if (selected.id === 'coordination_inter_lots' && (form.ifc_documents || []).length < 2) {
      setError('La coordination nécessite au moins 2 maquettes IFC (une par lot).');
      return;
    }
    if (selected.id === 'releve_thermique_2d' && (form.plan_documents || []).length < 1) {
      setError('Ajoutez au moins un plan (PDF ou image) à relever.');
      return;
    }
    setSubmitting(true);
    setError(null);

    try {
      const payload = buildTaskPayload(selected.id, form, projectId, uploadedDocId);
      await api.createTask(payload);
      router.push(projectId ? `/projects/${projectId}` : '/dashboard');
    } catch (e: any) {
      setError(e?.message || 'Erreur lors de la création de la tâche');
    } finally {
      setSubmitting(false);
    }
  };

  const handleFileUpload = async (files: File[]) => {
    setUploading(true);
    try {
      const f = files[0];
      const r = await api.uploadDocument(f, projectId || undefined);
      setUploadedDocId(r.id || r.document_id);
      setUploadedFileName(f.name);
    } catch (e: any) {
      setError(e?.message || 'Upload échoué');
    } finally {
      setUploading(false);
    }
  };

  // Étape 1 : sélection du type
  if (!selected) {
    return (
      <div className="space-y-6">
        <div>
          <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
            <ArrowLeft className="h-3.5 w-3.5" /> Tableau de bord
          </Link>
          <h1 className="text-2xl font-semibold mt-3">Nouvelle tâche</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Choisis le type de livrable à produire. Clique sur <HelpCircle className="inline h-3.5 w-3.5 -mt-0.5" /> pour savoir à quoi sert chaque livrable.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {TASK_CATEGORIES.map((c) => (
            <div
              key={c.id}
              role="button"
              tabIndex={0}
              onClick={() => setSelected(c)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelected(c); } }}
              className="group relative p-4 rounded-lg border bg-card text-left hover:border-muted-foreground/40 hover:shadow-sm transition-all focus-ring cursor-pointer"
            >
              {c.help && (
                <button
                  type="button"
                  aria-label={`Aide : ${c.title}`}
                  onClick={(e) => { e.stopPropagation(); setOpenHelp(openHelp === c.id ? null : c.id); }}
                  className="absolute top-2.5 right-2.5 z-10 p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  {openHelp === c.id ? <X className="h-4 w-4" /> : <HelpCircle className="h-4 w-4" />}
                </button>
              )}
              <div className={`inline-flex w-10 h-10 rounded-md ${c.color} items-center justify-center mb-3`}>
                <c.icon className="h-5 w-5" strokeWidth={1.8} />
              </div>
              <h3 className="font-medium text-sm mb-1.5 pr-6">{c.title}</h3>

              {openHelp === c.id && c.help ? (
                <div
                  className="text-xs leading-relaxed space-y-1.5 mb-1 rounded-md bg-muted/60 p-2.5"
                  onClick={(e) => e.stopPropagation()}
                >
                  <p><span className="font-semibold">À quoi ça sert : </span>{c.help.what}</p>
                  <p><span className="font-semibold">Prérequis : </span>{c.help.prereq}</p>
                  {c.help.tips && (
                    <p className="text-amber-700"><span className="font-semibold">Bon à savoir : </span>{c.help.tips}</p>
                  )}
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setSelected(c); }}
                    className="mt-1 inline-flex items-center gap-1 text-primary font-medium hover:underline"
                  >
                    Choisir ce livrable <ArrowRight className="h-3 w-3" />
                  </button>
                </div>
              ) : (
                <>
                  <p className="text-xs text-muted-foreground leading-relaxed mb-3">
                    {c.description}
                  </p>
                  <div className="flex items-center justify-between">
                    {c.days_saved ? (
                      <span className="text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                        {c.days_saved}
                      </span>
                    ) : (
                      <span />
                    )}
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Si redirect module, on affiche rien le temps du redirect
  if (selected.fields.some((f) => f.startsWith('redirect_'))) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Redirection vers le module…
      </div>
    );
  }

  // Étape 2 : formulaire
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <button
          onClick={() => setSelected(null)}
          className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Changer de type
        </button>
        <div className="flex items-start gap-3 mt-3">
          <div className={`inline-flex w-10 h-10 rounded-md ${selected.color} items-center justify-center shrink-0`}>
            <selected.icon className="h-5 w-5" strokeWidth={1.8} />
          </div>
          <div>
            <h1 className="text-xl font-semibold">{selected.title}</h1>
            <p className="text-sm text-muted-foreground mt-0.5">{selected.description}</p>
          </div>
        </div>
      </div>

      {error && <Banner variant="error">{error}</Banner>}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Projet lié - toujours visible */}
        <div>
          <Label>Projet lié (optionnel)</Label>
          <Select value={projectId || '__none'} onValueChange={(v) => setProjectId(v === '__none' ? '' : v)}>
            <SelectTrigger><SelectValue placeholder="Aucun projet" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__none">Aucun</SelectItem>
              {projects.map((p) => (
                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Champs adaptatifs */}
        <AdaptiveFields
          fields={selected.fields}
          form={form}
          setForm={setForm}
          onFileUpload={handleFileUpload}
          uploadedFileName={uploadedFileName}
          uploading={uploading}
          projectId={projectId}
        />

        <div className="flex items-center gap-3 pt-2">
          <Button type="submit" disabled={submitting} className="gap-2">
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {submitting ? 'En cours de génération…' : 'Lancer la tâche'}
          </Button>
          <button
            type="button"
            onClick={() => setSelected(null)}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Annuler
          </button>
        </div>
      </form>
    </div>
  );
}

function AdaptiveFields({
  fields, form, setForm, onFileUpload, uploadedFileName, uploading, projectId,
}: {
  fields: string[]; form: any; setForm: (f: any) => void;
  onFileUpload: (files: File[]) => Promise<void>;
  uploadedFileName: string; uploading: boolean; projectId?: string;
}) {
  const setField = (k: string, v: any) => setForm({ ...form, [k]: v });

  return (
    <>
      {fields.includes('project_name') && (
        <div>
          <Label>Nom du projet *</Label>
          <Input required value={form.project_name || ''}
            onChange={(e) => setField('project_name', e.target.value)} />
        </div>
      )}

      {fields.includes('canton') && (
        <div>
          <Label>Canton *</Label>
          <Select value={form.canton || 'GE'} onValueChange={(v) => setField('canton', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {CANTONS_ROMANDS.map((c) => (
                <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {fields.includes('address') && (
        <div>
          <Label>Adresse</Label>
          <Input value={form.address || ''} onChange={(e) => setField('address', e.target.value)} />
        </div>
      )}

      {fields.includes('affectation') && (
        <div>
          <Label>Affectation *</Label>
          <Select value={form.affectation || 'logement_collectif'}
            onValueChange={(v) => setField('affectation', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {AFFECTATIONS_SIA.map((a) => (
                <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {fields.includes('operation_type') && (
        <div>
          <Label>Type d'opération *</Label>
          <Select value={form.operation_type || 'neuf'}
            onValueChange={(v) => setField('operation_type', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="neuf">Construction neuve</SelectItem>
              <SelectItem value="renovation">Rénovation</SelectItem>
              <SelectItem value="transformation">Transformation</SelectItem>
              <SelectItem value="surelevation">Surélévation</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {fields.includes('sre_m2') && (
        <div>
          <Label>SRE (m²) *</Label>
          <Input required type="number" step="1" value={form.sre_m2 || ''}
            onChange={(e) => setField('sre_m2', e.target.value)} />
        </div>
      )}

      {fields.includes('nb_logements') && (
        <div>
          <Label>Nombre de logements</Label>
          <Input type="number" value={form.nb_logements || ''}
            onChange={(e) => setField('nb_logements', e.target.value)} />
        </div>
      )}

      {fields.includes('lot') && (
        <div>
          <Label>Lot *</Label>
          <Select value={form.lot || 'cvs'} onValueChange={(v) => setField('lot', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="cvs">Chauffage / CVS</SelectItem>
              <SelectItem value="ventilation">Ventilation</SelectItem>
              <SelectItem value="sanitaire">Sanitaire</SelectItem>
              <SelectItem value="electricite">Électricité</SelectItem>
              <SelectItem value="mcr">MCR / GTB</SelectItem>
              <SelectItem value="gros_oeuvre">Gros œuvre (béton, maçonnerie)</SelectItem>
              <SelectItem value="facade">Façade / enveloppe</SelectItem>
              <SelectItem value="second_oeuvre">Second œuvre (plâtrerie, sols, peinture)</SelectItem>
              <SelectItem value="ascenseur">Ascenseurs</SelectItem>
              <SelectItem value="custom">Autre lot (à décrire) …</SelectItem>
            </SelectContent>
          </Select>
          {form.lot === 'custom' ? (
            <div className="mt-2">
              <Input
                value={form.lot_custom || ''}
                placeholder="Nom du lot (ex. Serrurerie / métallerie, Cuisines, Stores…)"
                onChange={(e) => setField('lot_custom', e.target.value)}
              />
              <p className="text-[11px] text-muted-foreground mt-1">
                Lot libre : LESO construit le CCTP à partir des « Articles sur mesure » ci-dessous. Pensez à les renseigner.
              </p>
            </div>
          ) : (
            <p className="text-[11px] text-muted-foreground mt-1">
              Bibliothèque de prescriptions détaillée disponible pour tous les lots de la liste. Pour un lot hors liste, choisissez « Autre lot ».
            </p>
          )}
        </div>
      )}

      {fields.includes('type_ouvrage') && (
        <div>
          <Label>Type d'ouvrage</Label>
          <Input value={form.type_ouvrage || ''}
            placeholder="Ex: logement collectif neuf R+4"
            onChange={(e) => setField('type_ouvrage', e.target.value)} />
        </div>
      )}

      {fields.includes('niveau_prestation') && (
        <div>
          <Label>Niveau de prestation</Label>
          <Select value={form.niveau_prestation || 'standard'}
            onValueChange={(v) => setField('niveau_prestation', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="economique">Économique</SelectItem>
              <SelectItem value="standard">Standard</SelectItem>
              <SelectItem value="premium">Premium</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {fields.includes('surface') && (
        <div>
          <Label>Surface concernée (m²)</Label>
          <Input type="number" value={form.surface || ''}
            onChange={(e) => setField('surface', e.target.value)} />
        </div>
      )}

      {fields.includes('standard') && (
        <div>
          <Label>Standard énergétique</Label>
          <Select value={form.standard || 'sia_380_1_neuf'}
            onValueChange={(v) => setField('standard', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="sia_380_1_neuf">SIA 380/1 neuf</SelectItem>
              <SelectItem value="renovation_qualifiee">Rénovation qualifiée</SelectItem>
              <SelectItem value="minergie">MINERGIE</SelectItem>
              <SelectItem value="minergie_p">MINERGIE-P</SelectItem>
              <SelectItem value="existant_1980">Existant (avant 1980)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {fields.includes('heating_vector') && (
        <div>
          <Label>Vecteur chauffage</Label>
          <Select value={form.heating_vector || 'chauffage_distance'}
            onValueChange={(v) => setField('heating_vector', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="gaz">Gaz</SelectItem>
              <SelectItem value="mazout">Mazout</SelectItem>
              <SelectItem value="pellet">Pellets</SelectItem>
              <SelectItem value="chauffage_distance">CAD (réseau)</SelectItem>
              <SelectItem value="pac_air_eau">PAC air/eau</SelectItem>
              <SelectItem value="pac_sonde">PAC sonde géothermique</SelectItem>
              <SelectItem value="electrique">Électrique direct</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {fields.includes('facteur_forme') && (
        <div>
          <Label>Facteur de forme</Label>
          <Select value={form.facteur_forme || 'standard'}
            onValueChange={(v) => setField('facteur_forme', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="compact">Compact (A/V faible)</SelectItem>
              <SelectItem value="standard">Standard</SelectItem>
              <SelectItem value="etale">Étalé</SelectItem>
              <SelectItem value="tres_etale">Très étalé</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {fields.includes('building_type') && (
        <div>
          <Label>Typologie du bâtiment</Label>
          <Select value={form.building_type || 'habitation_faible'}
            onValueChange={(v) => setField('building_type', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="habitation_faible">Habitation - hauteur faible</SelectItem>
              <SelectItem value="habitation_moyenne">Habitation - hauteur moyenne</SelectItem>
              <SelectItem value="habitation_elevee">Habitation - hauteur élevée</SelectItem>
              <SelectItem value="administration">Administration</SelectItem>
              <SelectItem value="erp_petit">ERP petit</SelectItem>
              <SelectItem value="erp_moyen">ERP moyen</SelectItem>
              <SelectItem value="erp_grand">ERP grand</SelectItem>
              <SelectItem value="parking">Parking</SelectItem>
              <SelectItem value="industriel">Industriel</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {fields.includes('height_m') && (
        <div>
          <Label>Hauteur (m)</Label>
          <Input type="number" step="0.1" value={form.height_m || ''}
            onChange={(e) => setField('height_m', e.target.value)} />
        </div>
      )}

      {fields.includes('nb_occupants_max') && (
        <div>
          <Label>Occupants max</Label>
          <Input type="number" value={form.nb_occupants_max || ''}
            onChange={(e) => setField('nb_occupants_max', e.target.value)} />
        </div>
      )}

      {fields.includes('special_context') && (
        <div>
          <Label>Contexte particulier (optionnel)</Label>
          <Textarea rows={2} value={form.special_context || ''}
            placeholder="Ex: parking souterrain sur 2 niveaux avec accès véhicules"
            onChange={(e) => setField('special_context', e.target.value)} />
        </div>
      )}

      {fields.includes('brief') && (
        <div>
          <Label>Brief / CCTP client *</Label>
          <Textarea rows={5} value={form.brief || ''}
            placeholder="Collez le cahier des charges ou décrivez la demande : objet, attentes, contraintes, critères de notation…"
            onChange={(e) => setField('brief', e.target.value)} />
        </div>
      )}

      {fields.includes('elements') && (
        <div>
          <Label>Éléments / locaux à justifier</Label>
          <Textarea rows={3} value={form.elements || ''}
            placeholder="Ex : séparation logement/logement, façade sur rue, dalle entre commerce et logement…"
            onChange={(e) => setField('elements', e.target.value)} />
        </div>
      )}

      {fields.includes('hypotheses') && (
        <div>
          <Label>Hypothèses (optionnel)</Label>
          <Textarea rows={2} value={form.hypotheses || ''}
            placeholder="Ex : DnT,w visé 52 dB, L'nT,w ≤ 53 dB, dalle BA 22 cm + chape flottante…"
            onChange={(e) => setField('hypotheses', e.target.value)} />
        </div>
      )}

      {fields.includes('document_upload') && (
        <div>
          <Label>Document à résumer (PDF) *</Label>
          <Dropzone
            accept=".pdf"
            hint="Rapport, norme, étude… (max 50 Mo)"
            maxSizeMB={50}
            uploading={uploading}
            currentFileName={uploadedFileName}
            onFilesSelected={onFileUpload}
          />
        </div>
      )}

      {fields.includes('specificities') && (
        <div>
          <Label>Spécificités du projet</Label>
          <Textarea rows={3} value={form.specificities || ''}
            placeholder="Contraintes particulières, éléments à mettre en avant, dérogations envisagées…"
            onChange={(e) => setField('specificities', e.target.value)} />
        </div>
      )}

      {fields.includes('articles_libres') && (
        <CctpCustomArticles
          value={form.articles_libres || ''}
          onChange={(v) => setField('articles_libres', v)}
        />
      )}

      {fields.includes('contraintes') && (
        <div>
          <Label>Contraintes</Label>
          <Textarea rows={2} value={form.contraintes || ''}
            onChange={(e) => setField('contraintes', e.target.value)} />
        </div>
      )}

      {fields.includes('notes') && (
        <div>
          <Label>Notes</Label>
          <Textarea rows={3} value={form.notes || ''}
            onChange={(e) => setField('notes', e.target.value)} />
        </div>
      )}

      {fields.includes('meeting_title') && (
        <div>
          <Label>Intitulé de la réunion</Label>
          <Input value={form.meeting_title || ''}
            onChange={(e) => setField('meeting_title', e.target.value)} />
        </div>
      )}

      {fields.includes('meeting_date') && (
        <div>
          <Label>Date de la réunion</Label>
          <Input type="date" value={form.meeting_date || ''}
            onChange={(e) => setField('meeting_date', e.target.value)} />
        </div>
      )}

      {fields.includes('meeting_heure') && (
        <div>
          <Label>Heure de la réunion</Label>
          <Input type="time" value={form.meeting_heure || ''}
            onChange={(e) => setField('meeting_heure', e.target.value)} />
        </div>
      )}

      {fields.includes('meeting_lieu') && (
        <div>
          <Label>Lieu</Label>
          <Input value={form.meeting_lieu || ''}
            placeholder="Bureau, visioconférence, chantier…"
            onChange={(e) => setField('meeting_lieu', e.target.value)} />
        </div>
      )}

      {fields.includes('authority') && (
        <div>
          <Label>Autorité émettrice</Label>
          <Input value={form.authority || ''}
            placeholder="Ex : DALE (GE), DGT (VD), CAMAC, commune…"
            onChange={(e) => setField('authority', e.target.value)} />
        </div>
      )}

      {fields.includes('participants') && (
        <div>
          <Label>Participants (nom et qualité)</Label>
          <Input value={form.participants || ''}
            placeholder="Théo Tran-van (BET CVC), Marie Fontaine (Architecte)…"
            onChange={(e) => setField('participants', e.target.value)} />
          <p className="text-xs text-muted-foreground mt-1">
            Séparez par des virgules. Indiquez la qualité entre parenthèses : « Nom (rôle) ».
            Elle est reprise telle quelle dans le compte-rendu.
          </p>
        </div>
      )}

      {fields.includes('author') && (
        <div>
          <Label>Ingénieur signataire</Label>
          <Input value={form.author || ''} placeholder="Nom prénom"
            onChange={(e) => setField('author', e.target.value)} />
        </div>
      )}

      {fields.includes('ifc_upload') && (
        <div>
          <Label>Fichier IFC *</Label>
          <Dropzone
            accept=".ifc,.ifczip"
            hint="Glisse ton IFC (max 50 Mo)"
            maxSizeMB={50}
            uploading={uploading}
            currentFileName={uploadedFileName}
            onFilesSelected={onFileUpload}
          />
        </div>
      )}

      {fields.includes('autorite_pdf_upload') && (
        <div>
          <Label>Courrier de l'autorité (PDF) *</Label>
          <Dropzone
            accept=".pdf"
            hint="DALE, DGT, CAMAC ou autre"
            uploading={uploading}
            currentFileName={uploadedFileName}
            onFilesSelected={onFileUpload}
          />
        </div>
      )}

      {fields.includes('ifc_multi_upload') && (
        <MultiIfcUpload
          projectId={projectId}
          items={form.ifc_documents || []}
          onChange={(items) => setField('ifc_documents', items)}
        />
      )}

      {fields.includes('plan_multi_upload') && (
        <MultiPlanUpload
          projectId={projectId}
          items={form.plan_documents || []}
          onChange={(items) => setField('plan_documents', items)}
        />
      )}
    </>
  );
}

type PlanEntry = { document_id: string; filename: string };

function MultiPlanUpload({
  projectId, items, onChange,
}: {
  projectId?: string;
  items: PlanEntry[];
  onChange: (items: PlanEntry[]) => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const addFiles = async (files: File[]) => {
    if (!files.length) return;
    setErr(null);
    setUploading(true);
    try {
      const added: PlanEntry[] = [];
      for (const f of files) {
        const r = await api.uploadDocument(f, projectId || undefined);
        added.push({ document_id: r.id || r.document_id, filename: f.name });
      }
      onChange([...items, ...added]);
    } catch (e: any) {
      setErr(e?.message || 'Upload échoué');
    } finally {
      setUploading(false);
    }
  };

  const remove = (i: number) => onChange(items.filter((_, idx) => idx !== i));

  return (
    <div className="space-y-3">
      <Label>Plans (PDF ou images) * — façades, étages, toiture, coupes</Label>
      <p className="text-xs text-muted-foreground -mt-1">
        Déposez vos planches d'architecte. Pour les façades, gardez le titre d'orientation
        (« Façade Sud-Ouest »…) : LESO lit l'orientation depuis la planche.
      </p>

      {items.length > 0 && (
        <ul className="space-y-1.5">
          {items.map((it, i) => (
            <li key={i} className="flex items-center justify-between rounded-md border bg-muted/30 px-3 py-2 text-sm">
              <span>{it.filename}</span>
              <button type="button" onClick={() => remove(i)} className="text-xs text-red-600 hover:underline">
                Retirer
              </button>
            </li>
          ))}
        </ul>
      )}

      <Dropzone
        accept=".pdf,.png,.jpg,.jpeg"
        hint="Glissez vos plans (PDF/images, plusieurs fichiers possibles)"
        maxSizeMB={50}
        uploading={uploading}
        onFilesSelected={addFiles}
      />
      {err && <p className="text-xs text-red-600">{err}</p>}
    </div>
  );
}

type IfcLotEntry = { lot: string; document_id: string; filename: string };

function MultiIfcUpload({
  projectId, items, onChange,
}: {
  projectId?: string;
  items: IfcLotEntry[];
  onChange: (items: IfcLotEntry[]) => void;
}) {
  const [lot, setLot] = useState('');
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const addFile = async (files: File[]) => {
    const f = files[0];
    if (!f) return;
    if (!lot.trim()) {
      setErr('Indique le nom du lot avant d\'ajouter le fichier.');
      return;
    }
    setErr(null);
    setUploading(true);
    try {
      const r = await api.uploadDocument(f, projectId || undefined);
      onChange([...items, { lot: lot.trim(), document_id: r.id || r.document_id, filename: f.name }]);
      setLot('');
    } catch (e: any) {
      setErr(e?.message || 'Upload échoué');
    } finally {
      setUploading(false);
    }
  };

  const remove = (i: number) => onChange(items.filter((_, idx) => idx !== i));

  return (
    <div className="space-y-3">
      <Label>Maquettes IFC par lot * (au moins 2)</Label>

      {items.length > 0 && (
        <ul className="space-y-1.5">
          {items.map((it, i) => (
            <li key={i} className="flex items-center justify-between rounded-md border bg-muted/30 px-3 py-2 text-sm">
              <span><strong>{it.lot}</strong> — {it.filename}</span>
              <button type="button" onClick={() => remove(i)} className="text-xs text-red-600 hover:underline">
                Retirer
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="rounded-md border border-dashed p-3 space-y-2">
        <Input
          placeholder="Nom du lot (ex. Structure, CVC, Sanitaire)"
          value={lot}
          onChange={(e) => setLot(e.target.value)}
        />
        <Dropzone
          accept=".ifc,.ifczip"
          hint="Glisse l'IFC de ce lot (max 50 Mo)"
          maxSizeMB={50}
          uploading={uploading}
          onFilesSelected={addFile}
        />
        {err && <p className="text-xs text-red-600">{err}</p>}
      </div>

      {items.length === 1 && (
        <p className="text-xs text-amber-600">Ajoute au moins un 2e lot pour lancer la coordination.</p>
      )}
    </div>
  );
}

// Catalogue d'articles CCTP réutilisables — mémorisé sur le navigateur,
// même logique que le catalogue de compositions thermiques.
const CCTP_CATALOG_KEY = 'leso_cctp_articles_v1';
type CctpSnippet = { name: string; content: string };

function loadCctpCatalog(): CctpSnippet[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(CCTP_CATALOG_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveCctpCatalog(items: CctpSnippet[]) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(CCTP_CATALOG_KEY, JSON.stringify(items));
  } catch {
    /* quota / mode privé : on ignore */
  }
}

function CctpCustomArticles({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [catalog, setCatalog] = useState<CctpSnippet[]>(loadCctpCatalog);
  const [showCatalog, setShowCatalog] = useState(false);
  const [snippetName, setSnippetName] = useState('');

  const saveSnippet = () => {
    const name = snippetName.trim();
    if (!name || !value.trim()) return;
    const next = [{ name, content: value }, ...catalog.filter((s) => s.name !== name)].slice(0, 50);
    setCatalog(next);
    saveCctpCatalog(next);
    setSnippetName('');
  };
  const insertSnippet = (s: CctpSnippet) => {
    onChange(value.trim() ? `${value.trim()}\n\n${s.content}` : s.content);
  };
  const removeSnippet = (name: string) => {
    const next = catalog.filter((s) => s.name !== name);
    setCatalog(next);
    saveCctpCatalog(next);
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <Label>Articles & prescriptions sur mesure (optionnel)</Label>
        <button
          type="button"
          onClick={() => setShowCatalog((v) => !v)}
          className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
        >
          <Library className="h-3.5 w-3.5" /> Mes modèles ({catalog.length})
        </button>
      </div>
      <Textarea
        rows={5}
        value={value}
        placeholder={'Saisissez librement vos exigences — LESO les intègre telles quelles au CCTP.\n\nEx :\n- Robinetterie : mitigeurs thermostatiques, corps laiton chromé\n- Garantie décennale exigée sur l’étanchéité de toiture\n- Compteur d’énergie thermique communicant M-Bus par logement'}
        onChange={(e) => onChange(e.target.value)}
      />
      <p className="text-[11px] text-muted-foreground mt-1">
        Tout ce que vous écrivez ici fait foi : LESO le structure en CCTP sans altérer vos valeurs. Idéal pour un lot absent de la liste ou une exigence client spécifique.
      </p>

      {showCatalog && (
        <div className="mt-2 rounded-md border bg-muted/30 p-3 space-y-2">
          <div className="flex items-center gap-2">
            <Input
              className="h-8"
              placeholder="Nom du modèle (ex. Sanitaire haut de gamme)"
              value={snippetName}
              onChange={(e) => setSnippetName(e.target.value)}
            />
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="gap-1 shrink-0"
              onClick={saveSnippet}
              disabled={!snippetName.trim() || !value.trim()}
            >
              <Bookmark className="h-3.5 w-3.5" /> Mémoriser
            </Button>
          </div>
          {catalog.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Aucun modèle enregistré. Saisissez vos articles puis mémorisez-les pour les réutiliser sur vos prochains projets.
            </p>
          ) : (
            <ul className="space-y-1">
              {catalog.map((s) => (
                <li key={s.name} className="flex items-center justify-between gap-2 text-sm">
                  <button
                    type="button"
                    className="flex-1 text-left hover:underline truncate"
                    onClick={() => insertSnippet(s)}
                    title="Insérer dans le champ"
                  >
                    {s.name}
                  </button>
                  <button
                    type="button"
                    onClick={() => removeSnippet(s.name)}
                    className="text-muted-foreground hover:text-red-600"
                    title="Supprimer ce modèle"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function buildTaskPayload(
  taskType: string,
  form: any,
  projectId: string,
  uploadedDocId: string | null,
): any {
  const base: any = {
    task_type: taskType,
    project_id: projectId || null,
    input_params: {},
  };

  const p = base.input_params;

  // Champs universels
  if (form.project_name) p.project_name = form.project_name;
  if (form.author) p.author = form.author;

  // Par type
  if (taskType === 'dossier_mise_enquete') {
    p.project_data = {
      canton: form.canton || 'GE',
      address: form.address || '',
      affectation: form.affectation,
      operation_type: form.operation_type,
      sre_m2: form.sre_m2 ? Number(form.sre_m2) : undefined,
    };
    p.specificities = form.specificities || '';
  } else if (taskType === 'metres_automatiques_ifc') {
    p.ifc_document_id = uploadedDocId;
  } else if (taskType === 'releve_thermique_2d') {
    if (form.canton) p.canton = form.canton;
    p.plan_documents = (form.plan_documents || []).map((d: any) => ({ document_id: d.document_id }));
  } else if (taskType === 'coordination_inter_lots') {
    p.ifc_documents = (form.ifc_documents || []).map((d: any) => ({
      lot: d.lot, document_id: d.document_id,
    }));
  } else if (taskType === 'reponse_observations_autorite') {
    // L'agent attend observations_document_id + project_context (pas project_data)
    p.observations_document_id = uploadedDocId;
    if (form.authority) p.authority = form.authority;
    p.project_context = {
      canton: form.canton,
      sre_m2: form.sre_m2 ? Number(form.sre_m2) : undefined,
    };
    p.project_address = form.address || '';
  } else if (taskType === 'simulation_energetique_rapide') {
    // L'agent lit ces champs à plat dans input_params (pas sous "programme")
    p.canton = form.canton || 'GE';
    p.affectation = form.affectation;
    p.sre_m2 = form.sre_m2 ? Number(form.sre_m2) : undefined;
    p.standard = form.standard || 'sia_380_1_neuf';
    p.heating_vector = form.heating_vector || 'chauffage_distance';
    p.facteur_forme = form.facteur_forme || 'standard';
  } else if (taskType === 'redaction_cctp') {
    Object.assign(p, {
      lot: form.lot, type_ouvrage: form.type_ouvrage,
      niveau_prestation: form.niveau_prestation, surface: form.surface,
      contraintes: form.contraintes,
      articles_libres: form.articles_libres || '',
      lot_custom: form.lot === 'custom' ? (form.lot_custom || '') : '',
    });
  } else if (taskType === 'chiffrage_dpgf' || taskType === 'chiffrage_dqe') {
    // L'agent chiffre à partir de metre_text (ou metre_document_id), pas de
    // champs surface/notes isolés : on compose un métré minimal lisible.
    p.lot = form.lot;
    p.niveau_prestation = form.niveau_prestation || 'standard';
    const metreLines: string[] = [];
    if (form.surface) metreLines.push(`Surface concernée : ${form.surface} m²`);
    if (form.notes) metreLines.push(String(form.notes));
    if (metreLines.length) p.metre_text = metreLines.join('\n');
  } else if (taskType === 'memoire_technique') {
    p.brief = form.brief || '';
  } else if (taskType === 'calcul_acoustique') {
    // L'agent note_calcul lit elements/hypotheses ; localisation pilote SIA vs EC.
    p.elements = form.elements || '';
    p.hypotheses = form.hypotheses || '';
    p.localisation = 'Suisse';
  } else if (taskType === 'rapport_chantier') {
    // L'agent accepte des notes seules (sans photo) ; project_name déjà posé.
    p.notes = form.notes || '';
  } else if (taskType === 'resume_document') {
    p.document_id = uploadedDocId;
  } else if (taskType === 'controle_reglementaire_geneve') {
    p.project_data = {
      canton: form.canton, address: form.address,
      affectation: form.affectation, operation_type: form.operation_type,
      sre_m2: form.sre_m2 ? Number(form.sre_m2) : undefined,
      nb_logements: form.nb_logements ? Number(form.nb_logements) : undefined,
    };
  } else if (taskType === 'aeai_checklist_generation') {
    Object.assign(p, {
      building_type: form.building_type,
      height_m: form.height_m ? Number(form.height_m) : undefined,
      nb_occupants_max: form.nb_occupants_max ? Number(form.nb_occupants_max) : undefined,
      special_context: form.special_context || '',
    });
  } else if (taskType === 'compte_rendu_reunion') {
    // L'agent lit "objet" (pas meeting_title) et itère sur participants :
    // il faut une LISTE, sinon une string serait parcourue caractère par caractère.
    p.objet = form.meeting_title || 'Réunion de projet';
    if (form.meeting_date) {
      const [y, m, d] = String(form.meeting_date).split('-');
      p.date = d && m && y ? `${d}.${m}.${y}` : form.meeting_date;
    }
    if (form.meeting_heure) p.heure = form.meeting_heure;
    if (form.meeting_lieu) p.lieu = form.meeting_lieu;
    p.participants = form.participants
      ? String(form.participants).split(',').map((s) => s.trim()).filter(Boolean)
      : [];
    p.notes = form.notes;
  }

  return base;
}
