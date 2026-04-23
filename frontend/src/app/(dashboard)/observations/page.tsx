'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  MessageSquareWarning, Loader2, Plus, ArrowLeft, Download, ChevronRight,
  ArrowUpRight, FileText,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { TaskStatusBadge } from '@/components/ui/task-status';
import { Skeleton, SkeletonListItem } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { Banner } from '@/components/ui/banner';
import { Dropzone } from '@/components/ui/dropzone';
import { Badge } from '@/components/ui/badge';
import { formatDateTime } from '@/lib/utils';
import { CANTONS_ROMANDS } from '@/lib/ch';
import { useActiveProject } from '@/lib/active-project';

export default function ObservationsPage() {
  const { activeProject } = useActiveProject();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.v4.observations.list();
      setItems(r.responses || r.observations || []);
    } catch (e: any) {
      setError(e?.message || 'Erreur');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <MessageSquareWarning className="h-5 w-5 text-primary" />
            <h1 className="text-2xl font-semibold">Observations autorité</h1>
          </div>
          <p className="text-sm text-muted-foreground">
            Courrier DALE / DGT / CAMAC reçu → lettre de réponse argumentée point par point.
          </p>
        </div>
        {!creating && (
          <Button onClick={() => setCreating(true)} className="gap-2 shrink-0">
            <Plus className="h-4 w-4" /> Nouvelle réponse
          </Button>
        )}
      </div>

      {error && <Banner variant="error">{error}</Banner>}

      {creating && (
        <NewObservationForm
          activeProjectId={activeProject?.id}
          activeProjectName={activeProject?.name}
          onClose={() => setCreating(false)}
          onSuccess={() => { setCreating(false); load(); }}
        />
      )}

      {!creating && (
        <div>
          {loading ? (
            <div className="rounded-lg border bg-card divide-y">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="p-3"><SkeletonListItem /></div>
              ))}
            </div>
          ) : items.length === 0 ? (
            <div className="rounded-lg border bg-card">
              <EmptyState
                icon={MessageSquareWarning}
                title="Aucune réponse pour le moment"
                description="Téléverse le courrier de l'autorité, l'agent analyse les observations et génère une lettre de réponse argumentée."
                action={{ label: 'Traiter un courrier', onClick: () => setCreating(true) }}
              />
            </div>
          ) : (
            <div className="rounded-lg border bg-card divide-y">
              {items.map((t) => (
                <ObservationRow key={t.id} task={t} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ObservationRow({ task }: { task: any }) {
  const isDone = task.status === 'completed';
  return (
    <div className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors">
      <div className="w-9 h-9 rounded-md bg-muted grid place-items-center shrink-0">
        <FileText className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <Link href={`/tasks/${task.id}`} className="block">
          <p className="text-sm font-medium truncate hover:underline">
            {task.input_params?.project_name || 'Courrier autorité'}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {formatDateTime(task.created_at)}
            {task.input_params?.project_data?.canton && (
              <> · <Badge variant="outline" className="text-[10px] h-4 px-1">
                {task.input_params.project_data.canton}
              </Badge></>
            )}
          </p>
        </Link>
      </div>
      <TaskStatusBadge status={task.status} />
      {isDone && task.result_url && (
        <a
          href={task.result_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs hover:bg-background transition-colors"
        >
          <Download className="h-3 w-3" /> Télécharger
        </a>
      )}
      <Link href={`/tasks/${task.id}`} className="text-muted-foreground hover:text-foreground">
        <ChevronRight className="h-4 w-4" />
      </Link>
    </div>
  );
}

function NewObservationForm({
  activeProjectId, activeProjectName, onClose, onSuccess,
}: {
  activeProjectId?: string; activeProjectName?: string;
  onClose: () => void; onSuccess: () => void;
}) {
  const [form, setForm] = useState<any>({
    project_id: activeProjectId || '',
    project_name: activeProjectName || '',
    canton: 'GE',
    address: '',
    author: '',
  });
  const [docId, setDocId] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>('');
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (files: File[]) => {
    setUploading(true);
    setError(null);
    try {
      const f = files[0];
      const r = await api.uploadDocument(f, form.project_id || undefined);
      setDocId(r.id || r.document_id);
      setFileName(f.name);
    } catch (e: any) {
      setError(e?.message || 'Upload échoué');
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docId) {
      setError("Téléverse d'abord le PDF du courrier de l'autorité.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.v4.observations.create({
        project_id: form.project_id || null,
        project_name: form.project_name,
        autorite_pdf_document_id: docId,
        project_data: { canton: form.canton, address: form.address },
        author: form.author,
      });
      onSuccess();
    } catch (e: any) {
      setError(e?.message || 'Erreur');
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-lg border bg-card p-5 space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-medium">Traiter un courrier d'autorité</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            L'agent détecte les observations numérotées, les classifie par thème réglementaire, puis rédige une réponse argumentée.
          </p>
        </div>
        <button onClick={onClose} className="text-sm text-muted-foreground hover:text-foreground">
          Annuler
        </button>
      </div>

      {error && <Banner variant="error">{error}</Banner>}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Dropzone bien visible en haut */}
        <div>
          <Label className="mb-2 block">Courrier DALE / DGT / CAMAC (PDF) *</Label>
          <Dropzone
            accept=".pdf"
            maxSizeMB={25}
            uploading={uploading}
            currentFileName={fileName}
            label="Glisse le courrier PDF ici"
            hint="PyMuPDF extrait les observations numérotées"
            onFilesSelected={handleUpload}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label>Nom du projet *</Label>
            <Input required value={form.project_name}
              onChange={(e) => setForm({ ...form, project_name: e.target.value })} />
          </div>
          <div>
            <Label>Canton</Label>
            <Select value={form.canton} onValueChange={(v) => setForm({ ...form, canton: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {CANTONS_ROMANDS.map((c) => (
                  <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Adresse du projet</Label>
            <Input value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </div>
          <div>
            <Label>Ingénieur signataire</Label>
            <Input value={form.author} placeholder="Nom prénom"
              onChange={(e) => setForm({ ...form, author: e.target.value })} />
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2 border-t">
          <Button type="submit" disabled={submitting || !docId} className="gap-2">
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {submitting ? 'Génération en cours…' : 'Générer la réponse'}
          </Button>
          {!docId && (
            <p className="text-xs text-muted-foreground">
              Téléverse le PDF du courrier pour activer le bouton
            </p>
          )}
        </div>
      </form>
    </div>
  );
}
