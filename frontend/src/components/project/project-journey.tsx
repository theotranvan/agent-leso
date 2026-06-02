'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Check, Circle, ChevronRight, Sparkles, Lock, ArrowRight, Download,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Skeleton } from '@/components/ui/skeleton';

interface Props {
  projectId: string;
  onEditProject?: () => void;
}

const STATUS_META: Record<string, { color: string; bg: string }> = {
  completed: { color: '#16a34a', bg: '#dcfce7' },
  in_progress: { color: '#2E75B6', bg: '#e6f1fb' },
  not_started: { color: '#9ca3af', bg: '#f3f4f6' },
};

// Chaque action mène à sa page dédiée quand elle existe (interface riche),
// sinon au formulaire générique pré-sélectionné sur ce type.
const TASK_TYPE_ROUTES: Record<string, string> = {
  justificatif_sia_380_1: '/thermique',
  note_calcul_sia_260_267: '/structure',
  idc_geneve_rapport: '/idc',
  idc_extraction_facture: '/idc',
  aeai_checklist_generation: '/aeai',
  aeai_rapport: '/aeai',
  metres_automatiques_ifc: '/metres',
  simulation_energetique_rapide: '/simulation-rapide',
  prebim_generation: '/bim',
  dossier_mise_enquete: '/dossier-enquete',
  reponse_observations_autorite: '/observations',
  veille_romande: '/veille',
};

export function ProjectJourney({ projectId, onEditProject }: Props) {
  const router = useRouter();
  const [state, setState] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExportDossier = async () => {
    setExporting(true);
    setExportError(null);
    try {
      const blob = await api.exportDossier(projectId, true);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `dossier-${projectId}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setExportError(e?.userMessage || e?.message || 'Export impossible');
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    api.getProjectJourney(projectId)
      .then((s) => {
        setState(s);
        // ouvre par défaut la phase courante ou la première en cours
        const cur = s.phases.find((p: any) => p.is_current)
          || s.phases.find((p: any) => p.status === 'in_progress');
        if (cur) setExpanded(cur.key);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <Skeleton className="h-64 w-full" />;
  if (!state) return null;

  const startAction = (taskType: string) => {
    if (taskType === 'project_setup') {
      onEditProject?.();
      return;
    }
    const dedicated = TASK_TYPE_ROUTES[taskType];
    if (dedicated) {
      router.push(`${dedicated}?project=${projectId}`);
      return;
    }
    router.push(`/tasks/new?type=${taskType}&project=${projectId}`);
  };

  return (
    <div className="space-y-4">
      {/* Barre de progression globale + action recommandée */}
      <div className="rounded-lg border border-border/60 bg-secondary/30 p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Avancement du parcours</div>
            <div className="text-xs text-muted-foreground">
              {state.global_progress}% des phases principales complétées
            </div>
          </div>
          <button
            type="button"
            onClick={handleExportDossier}
            disabled={exporting}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-3 py-1.5 text-sm hover:bg-secondary disabled:opacity-60"
          >
            <Download className="h-3.5 w-3.5" /> {exporting ? 'Préparation…' : 'Dossier complet'}
          </button>
        </div>
        {exportError && (
          <p className="mt-2 text-xs text-destructive">{exportError}</p>
        )}
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-border/60">
          <div className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${state.global_progress}%` }} />
        </div>

        {state.next_recommended && (
          <button
            onClick={() => startAction(state.next_recommended.task_type)}
            className="mt-3 flex w-full items-center gap-2 rounded-lg bg-primary/10 px-3 py-2 text-left text-sm transition hover:bg-primary/15"
          >
            <Sparkles className="h-4 w-4 flex-shrink-0 text-primary" />
            <span className="flex-1">
              <span className="text-muted-foreground">Prochaine étape recommandée : </span>
              <span className="font-medium">{state.next_recommended.label}</span>
            </span>
            <ArrowRight className="h-4 w-4 flex-shrink-0 text-primary" />
          </button>
        )}
      </div>

      {/* Phases */}
      <div className="space-y-2">
        {state.phases.map((phase: any) => {
          const meta = STATUS_META[phase.status] || STATUS_META.not_started;
          const isOpen = expanded === phase.key;
          return (
            <div key={phase.key} className="rounded-lg border border-border/60 bg-background">
              <button
                onClick={() => setExpanded(isOpen ? null : phase.key)}
                className="flex w-full items-center gap-3 p-3 text-left"
              >
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full"
                  style={{ background: meta.bg, color: meta.color }}>
                  {phase.status === 'completed'
                    ? <Check className="h-4 w-4" />
                    : <span className="text-xs font-semibold">{phase.order}</span>}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{phase.label}</span>
                    {phase.sia_code !== '—' && (
                      <span className="rounded bg-secondary px-1.5 py-0.5 text-xs text-muted-foreground">
                        SIA {phase.sia_code}
                      </span>
                    )}
                    {phase.optional && (
                      <span className="text-xs text-muted-foreground">optionnel</span>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">{phase.progress}% complété</div>
                </div>
                <ChevronRight className={`h-4 w-4 flex-shrink-0 text-muted-foreground transition ${isOpen ? 'rotate-90' : ''}`} />
              </button>

              {isOpen && (
                <div className="border-t border-border/60 p-3 pt-2">
                  <p className="mb-3 text-xs text-muted-foreground">{phase.description}</p>
                  <div className="space-y-1.5">
                    {phase.actions_state.map((action: any) => (
                      <div key={action.task_type}
                        className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-secondary/50">
                        {action.done
                          ? <Check className="h-4 w-4 flex-shrink-0 text-green-600" />
                          : <Circle className="h-4 w-4 flex-shrink-0 text-muted-foreground/40" />}
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 text-sm">
                            {action.label}
                            {action.optional && (
                              <span className="text-xs text-muted-foreground">(option)</span>
                            )}
                            {action.approved && (
                              <span className="rounded bg-green-100 px-1.5 text-xs text-green-700">validé</span>
                            )}
                          </div>
                          {action.advisory && (
                            <div className="text-xs text-amber-600">{action.advisory}</div>
                          )}
                        </div>
                        {action.task_type === 'project_setup' ? (
                          <button
                            onClick={() => startAction(action.task_type)}
                            className="flex-shrink-0 rounded-md border border-border px-2 py-1 text-xs hover:bg-secondary"
                          >
                            {action.done ? 'Modifier' : 'Compléter'}
                          </button>
                        ) : !action.done && (
                          <button
                            onClick={() => startAction(action.task_type)}
                            className="flex-shrink-0 rounded-md border border-border px-2 py-1 text-xs hover:bg-secondary"
                          >
                            Lancer
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
