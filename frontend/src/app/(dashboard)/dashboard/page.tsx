'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { FolderKanban, FileText, ListChecks, Euro, ArrowRight, AlertTriangle } from 'lucide-react';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ConsumptionChart } from '@/components/dashboard/ConsumptionChart';
import { STATUS_LABELS, TASK_TYPE_LABELS, formatDateTime } from '@/lib/utils';

export default function DashboardPage() {
  const [overview, setOverview] = useState<any>(null);
  const [consumption, setConsumption] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.dashboardOverview(), api.dashboardConsumption(30)])
      .then(([ov, co]) => {
        setOverview(ov);
        setConsumption(co);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-muted-foreground">Chargement...</div>;
  if (!overview) return <div>Erreur de chargement</div>;

  const quotaPct = Math.round((overview.quota.used / Math.max(overview.quota.limit, 1)) * 100);

  const kpis = [
    { label: 'Projets actifs', value: overview.counts.projects, icon: FolderKanban },
    { label: 'Documents', value: overview.counts.documents, icon: FileText },
    { label: 'Tâches ce mois', value: overview.counts.tasks_month, icon: ListChecks },
    { label: 'Coût du mois', value: `${overview.cost_this_month_eur.toFixed(2)} €`, icon: Euro },
  ];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">Plan actuel : <span className="font-medium text-foreground">{overview.plan}</span></p>
        </div>
        <Button asChild>
          <Link href="/tasks/new">Nouvelle tâche <ArrowRight className="h-4 w-4 ml-2" /></Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((k) => {
          const Icon = k.icon;
          return (
            <Card key={k.label}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">{k.label}</p>
                    <p className="text-2xl font-semibold mt-1">{k.value}</p>
                  </div>
                  <Icon className="h-5 w-5 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Consommation - 30 derniers jours</CardTitle>
          </CardHeader>
          <CardContent>
            {consumption?.daily && consumption.daily.length > 0 ? (
              <ConsumptionChart data={consumption.daily} />
            ) : (
              <p className="text-sm text-muted-foreground">Aucune donnée</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quota mensuel</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>{overview.quota.used} tâches utilisées</span>
                <span className="text-muted-foreground">sur {overview.quota.limit}</span>
              </div>
              <Progress value={quotaPct} />
              <p className="text-xs text-muted-foreground mt-2">{quotaPct}% du quota consommé</p>
            </div>
            {quotaPct >= 80 && (
              <Button variant="outline" className="w-full" asChild>
                <Link href="/billing">Passer au plan supérieur</Link>
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Dernières tâches</CardTitle>
          </CardHeader>
          <CardContent>
            {overview.recent_tasks.length === 0 ? (
              <p className="text-sm text-muted-foreground">Aucune tâche pour le moment</p>
            ) : (
              <ul className="divide-y">
                {overview.recent_tasks.map((t: any) => {
                  const st = STATUS_LABELS[t.status];
                  return (
                    <li key={t.id} className="py-3 first:pt-0 last:pb-0">
                      <Link href={`/tasks/${t.id}`} className="flex items-center justify-between hover:bg-accent -mx-2 px-2 rounded-md transition-colors">
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{TASK_TYPE_LABELS[t.task_type] || t.task_type}</p>
                          <p className="text-xs text-muted-foreground">{formatDateTime(t.created_at)}</p>
                        </div>
                        <Badge className={st.color}>{st.label}</Badge>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              Alertes réglementaires
            </CardTitle>
          </CardHeader>
          <CardContent>
            {overview.alerts.length === 0 ? (
              <p className="text-sm text-muted-foreground">Aucune nouvelle alerte</p>
            ) : (
              <ul className="divide-y">
                {overview.alerts.map((a: any) => (
                  <li key={a.id} className="py-3 first:pt-0 last:pb-0">
                    <a href={a.url} target="_blank" rel="noopener noreferrer" className="block hover:bg-accent -mx-2 px-2 rounded-md transition-colors">
                      <p className="text-sm font-medium line-clamp-1">{a.title}</p>
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{a.content_summary}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {a.source} · {a.published_at ? formatDateTime(a.published_at) : ''}
                      </p>
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
