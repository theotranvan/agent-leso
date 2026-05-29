'use client';
import { useEffect, useState } from 'react';
import { TrendingUp, Clock, CheckCircle2, FileText, Gauge } from 'lucide-react';
import { api } from '@/lib/api';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';

const TASK_LABELS: Record<string, string> = {
  redaction_cctp: 'CCTP',
  justificatif_sia_380_1: 'Justificatif thermique',
  note_calcul_sia_260_267: 'Note de calcul structure',
  chiffrage_dpgf: 'DPGF',
  aeai_checklist_generation: 'Checklist AEAI',
  coordination_inter_lots: 'Coordination',
  idc_geneve_rapport: 'IDC',
  simulation_energetique_rapide: 'Simulation énergétique',
};

export default function AnalyticsPage() {
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.analytics().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-4 gap-3">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
      </div>
    );
  }

  if (!data || data.documents_produced === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
        <EmptyState icon={TrendingUp} title="Pas encore de données"
          description="Les statistiques apparaîtront dès que vous aurez produit des documents." />
      </div>
    );
  }

  const maxCount = Math.max(...(data.top_types || []).map((t: any) => t.count), 1);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Sur les 30 derniers jours · {data.documents_produced} documents produits
        </p>
      </div>

      {/* KPIs principaux */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="rounded-lg border border-border/60 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4 text-blue-600" /> Temps économisé
          </div>
          <div className="mt-1 text-2xl font-semibold">{data.days_saved} j</div>
          <div className="text-xs text-muted-foreground">jours-ingénieur</div>
        </div>
        <div className="rounded-lg border border-border/60 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <TrendingUp className="h-4 w-4 text-green-600" /> Valeur générée
          </div>
          <div className="mt-1 text-2xl font-semibold text-green-700">
            {data.chf_saved.toLocaleString('fr-CH')} CHF
          </div>
          <div className="text-xs text-muted-foreground">à 850 CHF/jour</div>
        </div>
        <div className="rounded-lg border border-border/60 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="h-4 w-4 text-green-600" /> Taux d'approbation
          </div>
          <div className="mt-1 text-2xl font-semibold">{data.approval_rate}%</div>
          <div className="text-xs text-muted-foreground">
            {data.approved} approuvés · {data.rejected} renvoyés
          </div>
        </div>
        <div className="rounded-lg border border-border/60 p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Gauge className="h-4 w-4 text-amber-600" /> Confiance moyenne
          </div>
          <div className="mt-1 text-2xl font-semibold">
            {data.avg_confidence != null ? `${data.avg_confidence}%` : '—'}
          </div>
          <div className="text-xs text-muted-foreground">score auto-calculé</div>
        </div>
      </div>

      {/* Types de documents */}
      <div className="rounded-lg border border-border/60 p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold">
          <FileText className="h-4 w-4" /> Documents les plus produits
        </h2>
        <div className="space-y-3">
          {(data.top_types || []).map((t: any) => (
            <div key={t.task_type} className="flex items-center gap-3">
              <div className="w-44 flex-shrink-0 text-sm">
                {TASK_LABELS[t.task_type] || t.task_type}
              </div>
              <div className="flex-1">
                <div className="h-6 rounded bg-primary/15"
                  style={{ width: `${(t.count / maxCount) * 100}%`, minWidth: '24px' }} />
              </div>
              <div className="w-8 text-right text-sm font-medium">{t.count}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
