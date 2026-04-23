'use client';
import { useEffect, useState, use } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, MapPin, Plus, Trash2, FileIcon, Download, Flame, Building,
  Building2, Shield, FileCheck2, ChevronRight, Upload, Loader2, AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { TaskStatusBadge } from '@/components/ui/task-status';
import { Skeleton, SkeletonListItem } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { Banner } from '@/components/ui/banner';
import { StatusDot } from '@/components/ui/status-dot';
import { Dropzone } from '@/components/ui/dropzone';
import { TASK_TYPE_LABELS, formatDate, formatDateTime, formatBytes } from '@/lib/utils';
import { useActiveProject } from '@/lib/active-project';

type Tab = 'tasks' | 'documents' | 'compliance';

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { setActiveProject } = useActiveProject();

  const [project, setProject] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('tasks');
  const [uploading, setUploading] = useState(false);

  const fetchAll = async () => {
    try {
      const [p, d, t] = await Promise.all([
        api.getProject(id),
        api.listProjectDocuments(id),
        api.listProjectTasks(id),
      ]);
      setProject(p);
      setDocuments(d.documents || []);
      setTasks(t.tasks || []);
      // Synchronise le projet actif
      setActiveProject({
        id: p.id, name: p.name, canton: p.canton,
        address: p.address, affectation: p.affectation,
      });
    } catch (e: any) {
      setError(e?.message || 'Erreur');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleUpload = async (files: File[]) => {
    setUploading(true);
    try {
      for (const f of files) {
        await api.uploadDocument(f, id);
      }
      await fetchAll();
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Supprimer ce document ?')) return;
    try {
      await api.deleteDocument(docId);
      await fetchAll();
    } catch (e: any) {
      alert(e.message);
    }
  };

  if (loading) return <ProjectSkeleton />;

  if (error || !project) {
    return (
      <div className="space-y-4">
        <Link href="/projects" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
          <ArrowLeft className="h-3.5 w-3.5" /> Retour aux projets
        </Link>
        <Banner variant="error">{error || 'Projet introuvable'}</Banner>
      </div>
    );
  }

  const complianceDims = buildComplianceDimensions(tasks);

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Link
        href="/projects"
        className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Tous les projets
      </Link>

      {/* Header projet */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold truncate">{project.name}</h1>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-sm text-muted-foreground">
            {project.address && (
              <span className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5" />
                {project.address}
              </span>
            )}
            {project.canton && <Badge variant="outline">{project.canton}</Badge>}
            {project.affectation && <span>{project.affectation}</span>}
            {project.sre_m2 && <span>{project.sre_m2} m² SRE</span>}
          </div>
        </div>
        <Link href={`/tasks/new?project_id=${project.id}`}>
          <Button className="gap-2 shrink-0">
            <Plus className="h-4 w-4" /> Nouvelle tâche
          </Button>
        </Link>
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-1">
          <TabButton active={tab === 'tasks'} onClick={() => setTab('tasks')} count={tasks.length}>
            Tâches
          </TabButton>
          <TabButton active={tab === 'documents'} onClick={() => setTab('documents')} count={documents.length}>
            Documents
          </TabButton>
          <TabButton active={tab === 'compliance'} onClick={() => setTab('compliance')}>
            Conformité
          </TabButton>
        </nav>
      </div>

      {/* Tab content */}
      {tab === 'tasks' && <TasksTab tasks={tasks} projectId={id} />}
      {tab === 'documents' && (
        <DocumentsTab
          documents={documents}
          uploading={uploading}
          onUpload={handleUpload}
          onDelete={handleDelete}
        />
      )}
      {tab === 'compliance' && <ComplianceTab dims={complianceDims} projectId={id} />}
    </div>
  );
}

function TabButton({
  children, active, onClick, count,
}: {
  children: React.ReactNode; active: boolean; onClick: () => void; count?: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`relative flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors
        ${active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
    >
      {children}
      {typeof count === 'number' && count > 0 && (
        <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
          {count}
        </span>
      )}
      {active && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
    </button>
  );
}

function TasksTab({ tasks, projectId }: { tasks: any[]; projectId: string }) {
  if (tasks.length === 0) {
    return (
      <EmptyState
        icon={FileCheck2}
        title="Pas encore de tâche pour ce projet"
        description="Lance ta première tâche — un CCTP, un justificatif, un dossier d'enquête."
        action={{ label: 'Nouvelle tâche', href: `/tasks/new?project_id=${projectId}` }}
      />
    );
  }
  return (
    <div className="rounded-lg border bg-card divide-y">
      {tasks.map((t) => {
        const label = TASK_TYPE_LABELS[t.task_type] || t.task_type;
        const isDone = t.status === 'completed';
        return (
          <div key={t.id} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors">
            <div className="flex-1 min-w-0">
              <Link href={`/tasks/${t.id}`} className="block">
                <p className="text-sm font-medium truncate hover:underline">{label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {formatDateTime(t.created_at)}
                  {t.cost_euros > 0 && <> · {t.cost_euros.toFixed(3)} €</>}
                </p>
              </Link>
            </div>
            <TaskStatusBadge status={t.status} />
            {isDone && t.result_url && (
              <a
                href={t.result_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs hover:bg-background transition-colors"
              >
                <Download className="h-3 w-3" /> Télécharger
              </a>
            )}
            <Link
              href={`/tasks/${t.id}`}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Détail"
            >
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
        );
      })}
    </div>
  );
}

function DocumentsTab({
  documents, uploading, onUpload, onDelete,
}: {
  documents: any[]; uploading: boolean;
  onUpload: (files: File[]) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  return (
    <div className="space-y-4">
      <Dropzone
        multiple
        uploading={uploading}
        accept=".pdf,.ifc,.xlsx,.xls,.docx,.doc,.jpg,.jpeg,.png,.txt"
        hint="PDF, IFC, XLSX, DOCX — jusqu'à 25 Mo par fichier"
        onFilesSelected={onUpload}
      />

      {documents.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-8">
          Aucun document. Téléverse tes plans, factures, rapports…
        </p>
      ) : (
        <div className="rounded-lg border bg-card divide-y">
          {documents.map((d) => (
            <div key={d.id} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors">
              <div className="w-9 h-9 rounded-md bg-muted grid place-items-center shrink-0">
                <FileIcon className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{d.filename}</p>
                <p className="text-xs text-muted-foreground">
                  {(d.file_type || '').toUpperCase()}
                  {d.size_bytes && <> · {formatBytes(d.size_bytes)}</>}
                  <> · {formatDate(d.created_at)}</>
                </p>
              </div>
              <button
                onClick={() => onDelete(d.id)}
                className="p-1.5 rounded-md text-muted-foreground hover:text-red-600 hover:bg-red-50 transition-colors"
                aria-label="Supprimer"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ComplianceTab({
  dims, projectId,
}: {
  dims: ReturnType<typeof buildComplianceDimensions>; projectId: string;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {dims.map((d) => (
        <div key={d.key} className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className="w-9 h-9 rounded-md bg-muted grid place-items-center shrink-0">
            <d.icon className="h-4 w-4 text-muted-foreground" strokeWidth={1.8} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <p className="text-sm font-medium">{d.label}</p>
              <StatusDot status={d.status} size="sm" />
            </div>
            <p className="text-xs text-muted-foreground">{d.description}</p>
            {d.lastDate && (
              <p className="text-xs text-muted-foreground mt-1">
                Dernière action : {formatDate(d.lastDate)}
              </p>
            )}
          </div>
          <Link
            href={d.action}
            className="text-xs text-primary hover:underline whitespace-nowrap"
          >
            {d.status === 'not_started' ? 'Démarrer' : 'Voir'}
          </Link>
        </div>
      ))}
    </div>
  );
}

function buildComplianceDimensions(tasks: any[]) {
  const byType = (types: string[]) =>
    tasks.find((t) => types.includes(t.task_type));

  const toStatus = (t: any): string => {
    if (!t) return 'not_started';
    return t.status;
  };

  const therm = byType(['justificatif_sia_380_1', 'simulation_energetique_rapide']);
  const struct = byType(['note_calcul_sia_260_267']);
  const idc = byType(['idc_geneve_rapport']);
  const aeai = byType(['aeai_rapport', 'aeai_checklist_generation']);
  const doss = byType(['dossier_mise_enquete']);
  const obs = byType(['reponse_observations_autorite']);

  return [
    {
      key: 'thermique', label: 'Thermique SIA 380/1', icon: Flame,
      description: 'Justificatif énergétique', status: toStatus(therm),
      lastDate: therm?.completed_at, action: '/thermique',
    },
    {
      key: 'structure', label: 'Structure SIA 260-267', icon: Building,
      description: 'Note de calcul + double-check', status: toStatus(struct),
      lastDate: struct?.completed_at, action: '/structure',
    },
    {
      key: 'idc', label: 'IDC Genève', icon: Building2,
      description: 'Calcul + formulaire OCEN', status: toStatus(idc),
      lastDate: idc?.completed_at, action: '/idc',
    },
    {
      key: 'aeai', label: 'AEAI (incendie)', icon: Shield,
      description: 'Checklist + rapport', status: toStatus(aeai),
      lastDate: aeai?.completed_at, action: '/aeai',
    },
    {
      key: 'dossier', label: 'Dossier mise en enquête', icon: FileCheck2,
      description: 'Mémoire + pièces', status: toStatus(doss),
      lastDate: doss?.completed_at, action: '/dossier-enquete',
    },
    {
      key: 'obs', label: 'Observations autorité', icon: AlertCircle,
      description: 'Réponses DALE/DGT', status: toStatus(obs),
      lastDate: obs?.completed_at, action: '/observations',
    },
  ];
}

function ProjectSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-32" />
      <div>
        <Skeleton className="h-8 w-96" />
        <div className="flex gap-3 mt-3">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>
      <Skeleton className="h-10 w-full" />
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => <SkeletonListItem key={i} />)}
      </div>
    </div>
  );
}
