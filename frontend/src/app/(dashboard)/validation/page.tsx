'use client';
import { useEffect, useState, useCallback } from 'react';
import {
  CheckCircle2, AlertTriangle, XCircle, ShieldCheck, ChevronRight,
  ThumbsUp, RotateCcw, Clock, Sparkles, ExternalLink, FileText, X,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { Banner } from '@/components/ui/banner';
import { Button } from '@/components/ui/button';
import { Drawer } from '@/components/ui/drawer';
import { PageHeader } from '@/components/ui/page-header';
import { formatDate } from '@/lib/utils';
import { RegenerateDialog } from '@/components/dashboard/regenerate-dialog';

const TASK_LABELS: Record<string, string> = {
  redaction_cctp: 'CCTP',
  justificatif_sia_380_1: 'Justificatif thermique SIA 380/1',
  note_calcul_sia_260_267: 'Note de calcul structure',
  chiffrage_dpgf: 'DPGF',
  aeai_rapport: 'Rapport AEAI',
  idc_geneve_rapport: 'Rapport IDC',
  coordination_inter_lots: 'Coordination inter-lots',
  dossier_mise_enquete: 'Dossier mise à l\'enquête',
};

function levelMeta(level: string) {
  switch (level) {
    case 'high':
      return { color: '#16a34a', bg: '#dcfce7', label: 'Confiance élevée', Icon: CheckCircle2 };
    case 'medium':
      return { color: '#d97706', bg: '#fef3c7', label: 'Confiance moyenne', Icon: AlertTriangle };
    default:
      return { color: '#dc2626', bg: '#fee2e2', label: 'Révision nécessaire', Icon: XCircle };
  }
}

export default function ValidationPage() {
  const [queue, setQueue] = useState<any[]>([]);
  const [counts, setCounts] = useState({ ready_to_approve: 0, pending_review: 0, needs_revision: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<any | null>(null);
  const [review, setReview] = useState<any | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [acting, setActing] = useState(false);
  const [showRegen, setShowRegen] = useState(false);
  const [docxLoading, setDocxLoading] = useState(false);
  const [toast, setToast] = useState<{ msg: string; variant: 'success' | 'info' } | null>(null);

  const handleDocx = async () => {
    if (!selected) return;
    setDocxLoading(true);
    try {
      await api.exportTaskDocx(selected.id);
    } catch (e: any) {
      alert(e?.userMessage || e?.message || 'Export Word échoué');
    } finally {
      setDocxLoading(false);
    }
  };

  const showToast = useCallback((msg: string, variant: 'success' | 'info' = 'success') => {
    setToast({ msg, variant });
    window.setTimeout(() => setToast(null), 5000);
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    api.getReviewQueue()
      .then((r) => { setQueue(r.queue || []); setCounts(r.counts); })
      .catch((e: any) => setError(e?.message || 'Erreur'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const openReview = async (task: any) => {
    setSelected(task);
    setDrawerOpen(true);
    setReview(null);
    try {
      const r = await api.getTaskReview(task.id);
      setReview(r);
    } catch (e: any) {
      setReview({ error: e?.message });
    }
  };

  const doApprove = async () => {
    if (!selected) return;
    setActing(true);
    try {
      await api.approveTask(selected.id);
      setDrawerOpen(false);
      showToast('Document validé — disponible dans le projet › Documents.');
      load();
    } catch (e: any) {
      alert(e?.message || 'Erreur lors de l\'approbation');
    } finally {
      setActing(false);
    }
  };

  // « Renvoyer » = repart réellement en correction : on ouvre le dialogue de
  // régénération (motifs + commentaire) qui relance l'agent sur ce feedback.
  const openReject = () => {
    if (!selected) return;
    setShowRegen(true);
  };

  const onRegenSuccess = () => {
    setShowRegen(false);
    setDrawerOpen(false);
    showToast('Renvoyé en correction — l\'agent régénère le document, il réapparaîtra ici.', 'info');
    load();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="À valider"
        description="Étape 3 : les livrables générés par l'agent, triés par niveau de confiance. Relis les points signalés, puis approuve et exporte le PDF final."
        icon={ShieldCheck}
      />

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-secondary/40 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="h-4 w-4 text-green-600" /> Prêts à approuver
          </div>
          <div className="mt-1 text-2xl font-semibold text-green-700">{counts.ready_to_approve}</div>
        </div>
        <div className="rounded-lg bg-secondary/40 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4 text-amber-600" /> À relire
          </div>
          <div className="mt-1 text-2xl font-semibold text-amber-700">{counts.pending_review}</div>
        </div>
        <div className="rounded-lg bg-secondary/40 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <XCircle className="h-4 w-4 text-red-600" /> Révision nécessaire
          </div>
          <div className="mt-1 text-2xl font-semibold text-red-700">{counts.needs_revision}</div>
        </div>
      </div>

      {error && <Banner variant="error">{error}</Banner>}

      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-20 w-full" />)}
        </div>
      ) : queue.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="Aucun document en attente"
          description="Tous les documents produits ont été validés. Les nouveaux apparaîtront ici automatiquement."
        />
      ) : (
        <div className="space-y-2">
          {queue.map((task) => {
            const meta = levelMeta(task.confidence_level);
            const nbAlerts = (task.confidence_alerts || []).length;
            return (
              <button
                key={task.id}
                onClick={() => openReview(task)}
                className="flex w-full items-center gap-4 rounded-lg border border-border/60 bg-background p-4 text-left transition hover:border-border hover:bg-secondary/30"
              >
                {/* Score circulaire */}
                <div
                  className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full font-semibold"
                  style={{ background: meta.bg, color: meta.color }}
                >
                  {task.confidence_score ?? '—'}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">
                      {TASK_LABELS[task.task_type] || task.task_type}
                    </span>
                    {task.review_status === 'ready_to_approve' && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                        <Sparkles className="h-3 w-3" /> Prêt
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 truncate text-sm text-muted-foreground">
                    {nbAlerts > 0
                      ? `${nbAlerts} point${nbAlerts > 1 ? 's' : ''} à vérifier`
                      : 'Aucun point bloquant signalé'}
                    {task.completed_at && ` · ${formatDate(task.completed_at)}`}
                  </p>
                </div>

                <ChevronRight className="h-5 w-5 flex-shrink-0 text-muted-foreground" />
              </button>
            );
          })}
        </div>
      )}

      {/* Drawer de revue ciblée */}
      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Validation du document">
        {!review ? (
          <div className="space-y-3 p-1">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : review.error ? (
          <Banner variant="error">{review.error}</Banner>
        ) : (
          <div className="space-y-5">
            {/* Score */}
            {(() => {
              const meta = levelMeta(review.confidence_level);
              return (
                <div
                  className="flex items-center gap-3 rounded-lg p-4"
                  style={{ background: meta.bg }}
                >
                  <meta.Icon className="h-6 w-6" style={{ color: meta.color }} />
                  <div>
                    <div className="font-semibold" style={{ color: meta.color }}>
                      {meta.label} — {review.confidence_score}%
                    </div>
                    <div className="text-sm" style={{ color: meta.color }}>
                      {review.summary}
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Alertes ciblées (Levier 2) */}
            {review.alerts && review.alerts.length > 0 ? (
              <div>
                <h3 className="mb-2 text-sm font-semibold">
                  Points à vérifier ({review.alerts.length})
                </h3>
                <ul className="space-y-2">
                  {review.alerts.map((a: string, i: number) => (
                    <li key={i} className="flex gap-2 rounded-md bg-amber-50 p-3 text-sm text-amber-900">
                      <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
                      <span>{a}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="rounded-md bg-green-50 p-3 text-sm text-green-800">
                Aucun point bloquant signalé par l'agent. Relecture rapide recommandée.
              </div>
            )}

            {/* Lire / récupérer le document avant de trancher */}
            <div className="flex gap-2">
              {review.result_url && (
                <a
                  href={review.result_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex flex-1 items-center justify-center gap-2 rounded-md border border-border/60 bg-background px-4 py-2.5 text-sm font-medium transition hover:bg-secondary/40"
                >
                  <ExternalLink className="h-4 w-4" /> Ouvrir le PDF
                </a>
              )}
              <button
                type="button"
                onClick={handleDocx}
                disabled={docxLoading}
                className="flex flex-1 items-center justify-center gap-2 rounded-md border border-border/60 bg-background px-4 py-2.5 text-sm font-medium transition hover:bg-secondary/40 disabled:opacity-60"
              >
                <FileText className="h-4 w-4" /> {docxLoading ? 'Export…' : 'Télécharger Word'}
              </button>
            </div>

            {/* Permission */}
            {!review.can_approve && (
              <Banner variant="warning">{review.approval_reason}</Banner>
            )}

            {/* Actions 1-clic (Levier 3) */}
            <div className="flex gap-3 border-t border-border/60 pt-4">
              <Button
                onClick={doApprove}
                disabled={!review.can_approve || acting}
                className="flex-1"
              >
                <ThumbsUp className="mr-2 h-4 w-4" /> Approuver
              </Button>
              <Button
                onClick={openReject}
                disabled={acting}
                variant="outline"
                className="flex-1"
              >
                <RotateCcw className="mr-2 h-4 w-4" /> Renvoyer
              </Button>
            </div>

            <div className="space-y-1.5 rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
              <p className="flex items-start gap-1.5">
                <ThumbsUp className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-600" />
                <span><strong>Approuver</strong> : engage votre validation professionnelle. Le PDF reste dans le projet › Documents, marqué validé.</span>
              </p>
              <p className="flex items-start gap-1.5">
                <RotateCcw className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
                <span><strong>Renvoyer</strong> : indiquez ce qui ne va pas, l'agent régénère le document. Il revient ensuite dans cette file.</span>
              </p>
            </div>
          </div>
        )}
      </Drawer>

      {/* « Renvoyer » → régénération réelle avec feedback */}
      {selected && (
        <RegenerateDialog
          taskId={selected.id}
          open={showRegen}
          onClose={() => setShowRegen(false)}
          onSuccess={onRegenSuccess}
          currentPreview={review?.result_preview || selected.result_preview}
          regenerationCount={review?.regeneration_count ?? 0}
        />
      )}

      {/* Notification transitoire (validation / renvoi) */}
      {toast && (
        <div
          className={`fixed bottom-6 right-6 z-[60] flex max-w-sm items-start gap-3 rounded-lg border px-4 py-3 shadow-lg animate-in fade-in slide-in-from-bottom-2 ${
            toast.variant === 'success'
              ? 'border-green-200 bg-green-50 text-green-900'
              : 'border-amber-200 bg-amber-50 text-amber-900'
          }`}
        >
          {toast.variant === 'success' ? (
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-green-600" />
          ) : (
            <RotateCcw className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
          )}
          <p className="text-sm leading-snug">{toast.msg}</p>
          <button
            onClick={() => setToast(null)}
            className="ml-1 shrink-0 rounded p-0.5 hover:bg-black/5"
            aria-label="Fermer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
