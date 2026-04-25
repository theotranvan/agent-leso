'use client';
import { useEffect, useState, use } from 'react';
import Link from 'next/link';
import {
  ArrowLeft, Download, Zap, RefreshCw, Loader2, AlertCircle, Sparkles, History,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Banner } from '@/components/ui/banner';
import { TaskStatusBadge } from '@/components/ui/task-status';
import { Skeleton } from '@/components/ui/skeleton';
import { TASK_TYPE_LABELS, formatDateTime } from '@/lib/utils';
import { RegenerateDialog, MAX_REGENERATIONS, REGENERATION_REASONS } from '@/components/dashboard/regenerate-dialog';

export default function TaskDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [task, setTask] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [showRegenDialog, setShowRegenDialog] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const fetchTask = async () => {
    try {
      const t = await api.getTask(id);
      setTask(t);
    } catch (e: any) {
      setError(e?.message || 'Erreur');
    }
  };

  useEffect(() => {
    fetchTask();
    const i = setInterval(() => {
      // Polling tant que tâche pas terminée
      if (task?.status !== 'completed' && task?.status !== 'failed') {
        fetchTask();
      }
    }, 3000);
    return () => clearInterval(i);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, task?.status]);

  if (!task && !error) return <TaskSkeleton />;
  if (error && !task) {
    return (
      <div className="space-y-4 max-w-4xl">
        <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
          <ArrowLeft className="h-3.5 w-3.5" /> Retour
        </Link>
        <Banner variant="error">{error}</Banner>
      </div>
    );
  }
  if (!task) return null;

  const taskLabel = TASK_TYPE_LABELS[task.task_type] || task.task_type;
  const isDone = task.status === 'completed';
  const isFailed = task.status === 'failed';
  const isWorking = task.status === 'running' || task.status === 'queued';
  const canRegenerate = (isDone || isFailed) && (task.regeneration_count || 0) < MAX_REGENERATIONS;
  const canRetry = isFailed;

  const regenCount = task.regeneration_count || 0;
  const regenHistory = task.regeneration_history || [];

  const isQuotaError = task.error_message?.includes('Quota mensuel atteint');

  return (
    <>
      <div className="space-y-6 max-w-4xl">
        {/* Breadcrumb */}
        <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
          <ArrowLeft className="h-3.5 w-3.5" /> Retour
        </Link>

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2.5 flex-wrap mb-1">
              <h1 className="text-2xl font-semibold truncate">{taskLabel}</h1>
              <TaskStatusBadge status={task.status} />
              {regenCount > 0 && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 inline-flex items-center gap-1">
                  <RefreshCw className="h-3 w-3" />
                  {regenCount} régénération{regenCount > 1 ? 's' : ''}
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              Créée le {formatDateTime(task.created_at)}
              {task.input_params?.project_name && <> · {task.input_params.project_name}</>}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {isDone && task.result_url && (
              <a
                href={task.result_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="default" className="gap-2">
                  <Download className="h-4 w-4" /> Télécharger
                </Button>
              </a>
            )}
            {canRegenerate && (
              <Button
                variant="outline"
                onClick={() => setShowRegenDialog(true)}
                className="gap-2"
              >
                <Zap className="h-4 w-4 text-amber-500" />
                Régénérer
                <span className="text-xs text-muted-foreground">
                  ({regenCount}/{MAX_REGENERATIONS})
                </span>
              </Button>
            )}
            {!canRegenerate && (isDone || isFailed) && (
              <Button variant="outline" disabled className="gap-2">
                <Zap className="h-4 w-4" />
                Limite atteinte
              </Button>
            )}
            {canRetry && !isQuotaError && (
              <Button
                variant="ghost"
                onClick={async () => {
                  try {
                    await api.retryTask(id);
                    await fetchTask();
                  } catch (e: any) {
                    setError(e?.message);
                  }
                }}
                className="gap-2"
              >
                <RefreshCw className="h-4 w-4" /> Relancer
              </Button>
            )}
          </div>
        </div>

        {/* En cours */}
        {isWorking && (
          <Banner variant="info">
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>L'agent travaille — actualisation toutes les 3 secondes…</span>
            </div>
          </Banner>
        )}

        {/* Erreur quota → propose achat pack */}
        {isQuotaError && (
          <Banner variant="warning" title="Quota mensuel atteint">
            <p className="mb-2">{task.error_message}</p>
            <Link href="/settings/billing">
              <Button size="sm" className="gap-2 mt-1">
                <Sparkles className="h-3.5 w-3.5" />
                Acheter un pack de tokens
              </Button>
            </Link>
          </Banner>
        )}

        {/* Erreur classique */}
        {isFailed && !isQuotaError && task.error_message && (
          <Banner variant="error" title="Échec de la tâche">
            {task.error_message}
          </Banner>
        )}

        {/* Aperçu résultat */}
        {isDone && task.result_preview && (
          <section className="rounded-lg border bg-card">
            <div className="px-4 py-3 border-b flex items-center justify-between">
              <h2 className="text-sm font-medium">Aperçu du résultat</h2>
              {task.result_url && (
                <a
                  href={task.result_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                >
                  <Download className="h-3 w-3" /> Télécharger le PDF
                </a>
              )}
            </div>
            <div className="p-4">
              <pre className="text-xs font-mono leading-relaxed whitespace-pre-wrap text-foreground/80 max-h-96 overflow-y-auto">
                {task.result_preview}
              </pre>
            </div>
          </section>
        )}

        {/* Stats consommation */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <StatCard label="Modèle utilisé" value={modelDisplay(task.model_used)} mono />
          <StatCard
            label="Tokens consommés"
            value={task.tokens_used?.toLocaleString('fr-CH') || '0'}
          />
          <StatCard
            label="Coût estimé"
            value={
              task.cost_euros
                ? `${Number(task.cost_euros).toFixed(4)} €`
                : task.cost_chf
                ? `${Number(task.cost_chf).toFixed(4)} CHF`
                : '—'
            }
          />
        </div>

        {/* Historique régénérations */}
        {regenHistory.length > 0 && (
          <section className="rounded-lg border bg-card">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-muted/30 transition-colors border-b"
            >
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-muted-foreground" />
                <h2 className="text-sm font-medium">
                  Historique des régénérations ({regenHistory.length})
                </h2>
              </div>
              <span className="text-xs text-muted-foreground">
                {showHistory ? 'Masquer' : 'Voir'}
              </span>
            </button>
            {showHistory && (
              <div className="divide-y">
                {regenHistory.map((h: any, i: number) => (
                  <div key={i} className="p-4 text-sm">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">Tentative {h.attempt}</span>
                      <span className="text-xs text-muted-foreground">{formatDateTime(h.at)}</span>
                    </div>
                    {h.reason && (
                      <div className="flex flex-wrap gap-1 mb-2">
                        {h.reason.split(',').map((r: string, j: number) => {
                          const found = REGENERATION_REASONS.find(rr => rr.code === r.trim());
                          return (
                            <span key={j} className="text-[11px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                              {found?.label || r}
                            </span>
                          );
                        })}
                      </div>
                    )}
                    {h.sections && h.sections.length > 0 && (
                      <p className="text-xs text-muted-foreground mb-2">
                        Sections ciblées : {h.sections.join(' · ')}
                      </p>
                    )}
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span>Modèle : <span className="font-mono">{modelDisplay(h.model_used)}</span></span>
                      {h.tokens > 0 && <span>{h.tokens.toLocaleString('fr-CH')} tokens</span>}
                      {h.cost_chf > 0 && <span>{h.cost_chf.toFixed(4)} CHF</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Paramètres */}
        {task.input_params && Object.keys(task.input_params).length > 0 && (
          <details className="rounded-lg border bg-card group">
            <summary className="px-4 py-3 cursor-pointer text-sm font-medium hover:bg-muted/30 transition-colors flex items-center justify-between">
              Paramètres d'entrée
              <span className="text-xs text-muted-foreground group-open:hidden">Voir</span>
              <span className="text-xs text-muted-foreground hidden group-open:inline">Masquer</span>
            </summary>
            <div className="border-t p-4">
              <pre className="text-xs bg-muted/40 p-3 rounded-md overflow-auto max-h-64">
                {JSON.stringify(task.input_params, null, 2)}
              </pre>
            </div>
          </details>
        )}
      </div>

      {/* Modal régénération */}
      <RegenerateDialog
        taskId={id}
        open={showRegenDialog}
        onClose={() => setShowRegenDialog(false)}
        onSuccess={() => {
          fetchTask();
        }}
        currentPreview={task.result_preview}
        regenerationCount={regenCount}
      />
    </>
  );
}

function StatCard({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-xs text-muted-foreground mb-1.5">{label}</p>
      <p className={`text-sm ${mono ? 'font-mono' : ''} font-medium`}>{value}</p>
    </div>
  );
}

function modelDisplay(model?: string | null): string {
  if (!model) return '—';
  if (model.includes('opus')) return 'Opus';
  if (model.includes('sonnet')) return 'Sonnet';
  if (model.includes('haiku')) return 'Haiku';
  return model;
}

function TaskSkeleton() {
  return (
    <div className="space-y-6 max-w-4xl">
      <Skeleton className="h-4 w-24" />
      <div>
        <Skeleton className="h-8 w-2/3 mb-2" />
        <Skeleton className="h-4 w-1/3" />
      </div>
      <div className="grid grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
      <Skeleton className="h-48" />
    </div>
  );
}
