'use client';
import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input, Textarea } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { TASK_TYPE_LABELS } from '@/lib/utils';

const TASK_CATEGORIES = [
  {
    group: 'Documents techniques',
    tasks: ['redaction_cctp', 'memoire_technique', 'doe_compilation'],
  },
  {
    group: 'Notes de calcul',
    tasks: ['note_calcul_structure', 'verification_eurocode', 'calcul_thermique_re2020', 'calcul_acoustique'],
  },
  {
    group: 'Chiffrage',
    tasks: ['chiffrage_dpgf', 'chiffrage_dqe'],
  },
  {
    group: 'BIM / Coordination',
    tasks: ['coordination_inter_lots', 'analyse_ifc'],
  },
  {
    group: 'Réunions & synthèses',
    tasks: ['compte_rendu_reunion', 'resume_document'],
  },
];

export default function NewTaskPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const prefillProject = searchParams.get('project_id');

  const [projects, setProjects] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [taskType, setTaskType] = useState('redaction_cctp');
  const [projectId, setProjectId] = useState<string>(prefillProject || '');
  const [sendEmail, setSendEmail] = useState(true);
  const [recipientEmails, setRecipientEmails] = useState('');
  const [params, setParams] = useState<Record<string, any>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listProjects().then((d) => setProjects(d.projects));
  }, []);

  useEffect(() => {
    if (projectId) {
      api.listProjectDocuments(projectId).then((d) => setDocuments(d.documents));
    } else {
      setDocuments([]);
    }
  }, [projectId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const emails = recipientEmails
        .split(',')
        .map((e) => e.trim())
        .filter(Boolean);

      const task = await api.createTask({
        task_type: taskType,
        project_id: projectId || null,
        input_params: params,
        send_email: sendEmail,
        recipient_emails: emails,
      });
      router.push(`/tasks/${task.id}`);
    } catch (e: any) {
      setError(e.message);
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <Link href="/dashboard" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4 mr-1" /> Retour
      </Link>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Nouvelle tâche</h1>
        <p className="text-sm text-muted-foreground mt-1">Lancez un traitement automatisé par l'agent IA</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Type de tâche</CardTitle>
          </CardHeader>
          <CardContent>
            <Select value={taskType} onValueChange={setTaskType}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {TASK_CATEGORIES.map((cat) => (
                  <div key={cat.group}>
                    <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">{cat.group}</div>
                    {cat.tasks.map((t) => (
                      <SelectItem key={t} value={t}>{TASK_TYPE_LABELS[t]}</SelectItem>
                    ))}
                  </div>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Contexte projet</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Projet (optionnel)</Label>
              <Select value={projectId || 'none'} onValueChange={(v) => setProjectId(v === 'none' ? '' : v)}>
                <SelectTrigger><SelectValue placeholder="Sélectionner un projet" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Aucun</SelectItem>
                  {projects.map((p) => (
                    <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Paramètres</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <TaskParamsForm
              taskType={taskType}
              params={params}
              setParams={setParams}
              documents={documents}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Livraison</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={sendEmail}
                onChange={(e) => setSendEmail(e.target.checked)}
                className="h-4 w-4"
              />
              Envoyer le résultat par email
            </label>
            {sendEmail && (
              <div className="space-y-2">
                <Label>Destinataires (séparés par des virgules)</Label>
                <Input
                  type="text"
                  placeholder="contact@client.com, ingenieur@bet.fr"
                  value={recipientEmails}
                  onChange={(e) => setRecipientEmails(e.target.value)}
                />
              </div>
            )}
          </CardContent>
        </Card>

        {error && <div className="text-sm text-destructive">{error}</div>}

        <div className="flex gap-2">
          <Button type="submit" disabled={submitting}>
            {submitting ? 'Envoi...' : 'Lancer la tâche'}
          </Button>
          <Button type="button" variant="outline" onClick={() => router.back()}>
            Annuler
          </Button>
        </div>
      </form>
    </div>
  );
}

// Formulaire paramètres dynamique selon task_type
function TaskParamsForm({
  taskType, params, setParams, documents,
}: {
  taskType: string;
  params: Record<string, any>;
  setParams: (p: Record<string, any>) => void;
  documents: any[];
}) {
  const update = (key: string, value: any) => setParams({ ...params, [key]: value });

  if (taskType === 'redaction_cctp') {
    return (
      <>
        <div className="space-y-2">
          <Label>Lot *</Label>
          <Select value={params.lot || ''} onValueChange={(v) => update('lot', v)}>
            <SelectTrigger><SelectValue placeholder="Choisir" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="electricite">Électricité</SelectItem>
              <SelectItem value="cvc">CVC</SelectItem>
              <SelectItem value="structure">Structure</SelectItem>
              <SelectItem value="facade">Façade</SelectItem>
              <SelectItem value="plomberie">Plomberie</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Type d'ouvrage</Label>
          <Input placeholder="Logement collectif, ERP R+6..." value={params.type_ouvrage || ''} onChange={(e) => update('type_ouvrage', e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>Niveau de prestation</Label>
          <Select value={params.niveau_prestation || 'standard'} onValueChange={(v) => update('niveau_prestation', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="standard">Standard</SelectItem>
              <SelectItem value="haut_de_gamme">Haut de gamme</SelectItem>
              <SelectItem value="thqe">Très haute qualité environnementale</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Surface (m²)</Label>
          <Input type="number" value={params.surface || ''} onChange={(e) => update('surface', e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>Contraintes particulières</Label>
          <Textarea rows={4} placeholder="Zone sismique, accessibilité PMR, budget contraint..." value={params.contraintes || ''} onChange={(e) => update('contraintes', e.target.value)} />
        </div>
      </>
    );
  }

  if (taskType.startsWith('note_calcul') || taskType === 'verification_eurocode' || taskType.startsWith('calcul_')) {
    return (
      <>
        <div className="space-y-2">
          <Label>Éléments à calculer / vérifier</Label>
          <Textarea rows={3} value={params.elements || ''} onChange={(e) => update('elements', e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>Hypothèses</Label>
          <Textarea rows={4} placeholder="Charges permanentes, charges d'exploitation, classes de matériaux..." value={params.hypotheses || ''} onChange={(e) => update('hypotheses', e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Localisation</Label>
            <Input placeholder="France / Suisse" value={params.localisation || 'France'} onChange={(e) => update('localisation', e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Zone climatique</Label>
            <Input placeholder="H1a, H2b, H3..." value={params.zone_climatique || ''} onChange={(e) => update('zone_climatique', e.target.value)} />
          </div>
        </div>
        <div className="space-y-2">
          <Label>Document IFC (optionnel)</Label>
          <Select value={params.ifc_document_id || 'none'} onValueChange={(v) => update('ifc_document_id', v === 'none' ? undefined : v)}>
            <SelectTrigger><SelectValue placeholder="Aucun fichier IFC" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Aucun</SelectItem>
              {documents.filter((d) => d.file_type === 'ifc').map((d) => (
                <SelectItem key={d.id} value={d.id}>{d.filename}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </>
    );
  }

  if (taskType === 'chiffrage_dpgf') {
    return (
      <>
        <div className="space-y-2">
          <Label>Lot *</Label>
          <Input value={params.lot || ''} onChange={(e) => update('lot', e.target.value)} required />
        </div>
        <div className="space-y-2">
          <Label>Métré source (PDF uploadé)</Label>
          <Select value={params.metre_document_id || 'none'} onValueChange={(v) => update('metre_document_id', v === 'none' ? undefined : v)}>
            <SelectTrigger><SelectValue placeholder="Sélectionner" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Aucun (métré textuel)</SelectItem>
              {documents.filter((d) => d.file_type === 'pdf').map((d) => (
                <SelectItem key={d.id} value={d.id}>{d.filename}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Métré textuel (si pas de PDF)</Label>
          <Textarea rows={6} value={params.metre_text || ''} onChange={(e) => update('metre_text', e.target.value)} />
        </div>
      </>
    );
  }

  if (taskType === 'chiffrage_dqe') {
    return (
      <>
        <div className="space-y-2">
          <Label>Lots à chiffrer (séparés par des virgules)</Label>
          <Input placeholder="gros_oeuvre, cvc, electricite, plomberie"
            value={(params.lots || []).join(', ')}
            onChange={(e) => update('lots', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
          />
        </div>
        <div className="space-y-2">
          <Label>Métré source</Label>
          <Select value={params.metre_document_id || 'none'} onValueChange={(v) => update('metre_document_id', v === 'none' ? undefined : v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Aucun</SelectItem>
              {documents.filter((d) => d.file_type === 'pdf').map((d) => (
                <SelectItem key={d.id} value={d.id}>{d.filename}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </>
    );
  }

  if (taskType === 'coordination_inter_lots') {
    return (
      <>
        <Label>Fichiers IFC à coordonner (minimum 2)</Label>
        <p className="text-xs text-muted-foreground">Associez chaque fichier IFC à son lot</p>
        <CoordinationInputs params={params} setParams={setParams} documents={documents.filter((d) => d.file_type === 'ifc')} />
      </>
    );
  }

  if (taskType === 'compte_rendu_reunion') {
    return (
      <>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Objet</Label>
            <Input value={params.objet || ''} onChange={(e) => update('objet', e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Date</Label>
            <Input type="date" value={params.date || ''} onChange={(e) => update('date', e.target.value)} />
          </div>
        </div>
        <div className="space-y-2">
          <Label>Lieu</Label>
          <Input value={params.lieu || ''} onChange={(e) => update('lieu', e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>Participants (un par ligne)</Label>
          <Textarea rows={4} value={(params.participants || []).join('\n')} onChange={(e) => update('participants', e.target.value.split('\n').filter(Boolean))} />
        </div>
        <div className="space-y-2">
          <Label>Notes ou transcription *</Label>
          <Textarea rows={10} value={params.notes || ''} onChange={(e) => update('notes', e.target.value)} required />
        </div>
      </>
    );
  }

  if (taskType === 'memoire_technique') {
    return (
      <div className="space-y-2">
        <Label>Brief / CCTP client *</Label>
        <Textarea rows={10} value={params.brief || ''} onChange={(e) => update('brief', e.target.value)} required />
      </div>
    );
  }

  if (taskType === 'resume_document') {
    return (
      <div className="space-y-2">
        <Label>Document à résumer</Label>
        <Select value={params.document_id || 'none'} onValueChange={(v) => update('document_id', v === 'none' ? undefined : v)}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Sélectionner</SelectItem>
            {documents.map((d) => (
              <SelectItem key={d.id} value={d.id}>{d.filename}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  }

  if (taskType === 'doe_compilation') {
    return (
      <>
        <div className="space-y-2">
          <Label>Date de réception</Label>
          <Input type="date" value={params.date_reception || ''} onChange={(e) => update('date_reception', e.target.value)} />
        </div>
        <div className="space-y-2">
          <Label>Intervenants (un par ligne)</Label>
          <Textarea rows={4} placeholder="Maître d'ouvrage : ...&#10;Architecte : ..." value={(params.intervenants || []).join('\n')} onChange={(e) => update('intervenants', e.target.value.split('\n').filter(Boolean))} />
        </div>
      </>
    );
  }

  return (
    <div className="space-y-2">
      <Label>Contenu / instructions</Label>
      <Textarea rows={6} value={params.content || ''} onChange={(e) => update('content', e.target.value)} />
    </div>
  );
}

function CoordinationInputs({ params, setParams, documents }: any) {
  const entries = params.ifc_documents || [];

  const add = () => {
    setParams({ ...params, ifc_documents: [...entries, { lot: '', document_id: '' }] });
  };
  const update = (idx: number, key: string, value: string) => {
    const next = [...entries];
    next[idx] = { ...next[idx], [key]: value };
    setParams({ ...params, ifc_documents: next });
  };
  const remove = (idx: number) => {
    setParams({ ...params, ifc_documents: entries.filter((_: any, i: number) => i !== idx) });
  };

  return (
    <div className="space-y-3">
      {entries.map((entry: any, idx: number) => (
        <div key={idx} className="flex gap-2 items-end">
          <div className="flex-1 space-y-2">
            <Label className="text-xs">Lot</Label>
            <Input placeholder="cvc, structure..." value={entry.lot} onChange={(e) => update(idx, 'lot', e.target.value)} />
          </div>
          <div className="flex-[2] space-y-2">
            <Label className="text-xs">Fichier IFC</Label>
            <Select value={entry.document_id || ''} onValueChange={(v) => update(idx, 'document_id', v)}>
              <SelectTrigger><SelectValue placeholder="Sélectionner" /></SelectTrigger>
              <SelectContent>
                {documents.map((d: any) => (
                  <SelectItem key={d.id} value={d.id}>{d.filename}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button type="button" variant="outline" size="sm" onClick={() => remove(idx)}>Supprimer</Button>
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" onClick={add}>+ Ajouter un lot</Button>
    </div>
  );
}
