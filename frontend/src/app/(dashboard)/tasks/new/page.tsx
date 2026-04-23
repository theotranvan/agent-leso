'use client';
import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, ArrowRight, Loader2, FileText, Flame, Building, Building2, Shield, Bell,
  Layers, FileCheck2, MessageSquareWarning, Ruler, Zap, Users, Calculator, BookOpen,
  PenTool, ScrollText,
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

type TaskCategory = {
  id: string;
  title: string;
  description: string;
  icon: any;
  color: string;
  fields: string[];  // champs du form à afficher
  days_saved?: string;
};

const TASK_CATEGORIES: TaskCategory[] = [
  // Livrables haute valeur
  {
    id: 'dossier_mise_enquete',
    title: 'Dossier mise en enquête',
    description: 'Mémoire justificatif APA/APC avec tableau SIA 416 et checklist des pièces à fournir',
    icon: FileCheck2, color: 'bg-purple-50 text-purple-700',
    days_saved: '5-10 j économisés',
    fields: ['project_name', 'canton', 'address', 'affectation', 'operation_type', 'sre_m2', 'specificities', 'author'],
  },
  {
    id: 'metres_automatiques_ifc',
    title: 'Métrés automatiques IFC',
    description: 'Extrait SRE, volumes et quantités par CFC depuis un IFC. Produit un DPGF pré-rempli.',
    icon: Ruler, color: 'bg-amber-50 text-amber-700',
    days_saved: '1-2 j économisés',
    fields: ['project_name', 'ifc_upload', 'author'],
  },
  {
    id: 'reponse_observations_autorite',
    title: 'Réponse aux observations',
    description: 'Lettre argumentée point par point depuis un courrier DALE, DGT ou CAMAC',
    icon: MessageSquareWarning, color: 'bg-red-50 text-red-700',
    days_saved: '1-3 j économisés',
    fields: ['project_name', 'canton', 'autorite_pdf_upload', 'author'],
  },
  {
    id: 'simulation_energetique_rapide',
    title: 'Simulation énergétique rapide',
    description: 'Estime Qh en 30 s depuis un programme — avant-projet ou concours, sans IFC',
    icon: Zap, color: 'bg-orange-50 text-orange-700',
    fields: ['project_name', 'canton', 'affectation', 'sre_m2', 'standard', 'heating_vector', 'facteur_forme'],
  },
  // Livrables courants
  {
    id: 'redaction_cctp',
    title: 'CCTP',
    description: 'Descriptif des prestations par lot — rédigé selon SIA 451',
    icon: ScrollText, color: 'bg-blue-50 text-blue-700',
    fields: ['project_name', 'lot', 'type_ouvrage', 'niveau_prestation', 'surface', 'contraintes'],
  },
  {
    id: 'chiffrage_dpgf',
    title: 'DPGF / Chiffrage',
    description: 'Devis quantitatif structuré par lot à partir du programme',
    icon: Calculator, color: 'bg-emerald-50 text-emerald-700',
    fields: ['project_name', 'lot', 'surface', 'notes'],
  },
  {
    id: 'justificatif_sia_380_1',
    title: 'Justificatif SIA 380/1',
    description: 'Thermique — requiert un modèle ou un IFC (redirige vers le module)',
    icon: Flame, color: 'bg-orange-50 text-orange-700',
    fields: ['redirect_thermique'],
  },
  {
    id: 'note_calcul_sia_260_267',
    title: 'Note structure SIA 260-267',
    description: 'SAF pour Scia/RFEM puis note de calcul (redirige vers le module)',
    icon: Building, color: 'bg-slate-50 text-slate-700',
    fields: ['redirect_structure'],
  },
  {
    id: 'idc_geneve_rapport',
    title: 'IDC Genève',
    description: 'Extraction factures, calcul, formulaire OCEN (redirige vers le module)',
    icon: Building2, color: 'bg-emerald-50 text-emerald-700',
    fields: ['redirect_idc'],
  },
  {
    id: 'aeai_checklist_generation',
    title: 'Checklist AEAI',
    description: 'Checklist incendie pour une typologie donnée',
    icon: Shield, color: 'bg-amber-50 text-amber-700',
    fields: ['project_name', 'building_type', 'height_m', 'nb_occupants_max', 'special_context'],
  },
  {
    id: 'controle_reglementaire_geneve',
    title: 'Contrôle réglementaire',
    description: 'Rapport pré-dépôt : zone, énergie, LDTR, AEAI, stationnement',
    icon: FileText, color: 'bg-blue-50 text-blue-700',
    fields: ['project_name', 'canton', 'address', 'affectation', 'operation_type', 'sre_m2', 'nb_logements'],
  },
  {
    id: 'compte_rendu_reunion',
    title: 'Compte-rendu de réunion',
    description: 'Résumé structuré depuis des notes ou un enregistrement de réunion',
    icon: Users, color: 'bg-slate-50 text-slate-700',
    fields: ['project_name', 'meeting_title', 'participants', 'notes'],
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
  const preselectedProject = searchParams.get('project_id');

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

  useEffect(() => {
    api.projects.list().then((r: any) => setProjects(r.projects || [])).catch(() => {});
  }, []);

  // Sync avec projet actif
  useEffect(() => {
    if (!projectId && activeProject?.id) setProjectId(activeProject.id);
  }, [activeProject, projectId]);

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
            Choisis le type de livrable à produire.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {TASK_CATEGORIES.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelected(c)}
              className="group relative p-4 rounded-lg border bg-card text-left hover:border-muted-foreground/40 hover:shadow-sm transition-all focus-ring"
            >
              <div className={`inline-flex w-10 h-10 rounded-md ${c.color} items-center justify-center mb-3`}>
                <c.icon className="h-5 w-5" strokeWidth={1.8} />
              </div>
              <h3 className="font-medium text-sm mb-1.5">{c.title}</h3>
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
            </button>
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
          <Select value={projectId} onValueChange={setProjectId}>
            <SelectTrigger><SelectValue placeholder="Aucun projet" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="">Aucun</SelectItem>
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
  fields, form, setForm, onFileUpload, uploadedFileName, uploading,
}: {
  fields: string[]; form: any; setForm: (f: any) => void;
  onFileUpload: (files: File[]) => Promise<void>;
  uploadedFileName: string; uploading: boolean;
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
                <SelectItem key={a.code} value={a.code}>{a.label}</SelectItem>
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
              <SelectItem value="cvs">CVS / Chauffage</SelectItem>
              <SelectItem value="electricite">Électricité</SelectItem>
              <SelectItem value="sanitaire">Sanitaire</SelectItem>
              <SelectItem value="mcr">MCR</SelectItem>
              <SelectItem value="structure">Structure</SelectItem>
              <SelectItem value="enveloppe">Enveloppe</SelectItem>
              <SelectItem value="second_oeuvre">Second œuvre</SelectItem>
            </SelectContent>
          </Select>
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

      {fields.includes('specificities') && (
        <div>
          <Label>Spécificités du projet</Label>
          <Textarea rows={3} value={form.specificities || ''}
            placeholder="Contraintes particulières, éléments à mettre en avant, dérogations envisagées…"
            onChange={(e) => setField('specificities', e.target.value)} />
        </div>
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

      {fields.includes('participants') && (
        <div>
          <Label>Participants</Label>
          <Input value={form.participants || ''}
            placeholder="Noms séparés par des virgules"
            onChange={(e) => setField('participants', e.target.value)} />
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
    </>
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
  } else if (taskType === 'reponse_observations_autorite') {
    p.autorite_pdf_document_id = uploadedDocId;
    p.project_data = { canton: form.canton, address: form.address };
  } else if (taskType === 'simulation_energetique_rapide') {
    p.programme = {
      canton: form.canton || 'GE',
      affectation: form.affectation,
      sre_m2: form.sre_m2 ? Number(form.sre_m2) : undefined,
      standard: form.standard || 'sia_380_1_neuf',
      heating_vector: form.heating_vector || 'chauffage_distance',
      facteur_forme: form.facteur_forme || 'standard',
    };
  } else if (taskType === 'redaction_cctp') {
    Object.assign(p, {
      lot: form.lot, type_ouvrage: form.type_ouvrage,
      niveau_prestation: form.niveau_prestation, surface: form.surface,
      contraintes: form.contraintes,
    });
  } else if (taskType === 'chiffrage_dpgf') {
    Object.assign(p, { lot: form.lot, surface: form.surface, notes: form.notes });
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
    Object.assign(p, {
      meeting_title: form.meeting_title,
      participants: form.participants,
      notes: form.notes,
    });
  }

  return base;
}
