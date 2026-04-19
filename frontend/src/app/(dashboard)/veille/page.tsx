'use client';
import { useEffect, useState } from 'react';
import { Bell, ExternalLink, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { StatusBadge } from '@/components/swiss/StatusBadge';
import { formatDateTime } from '@/lib/utils';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export default function VeillePage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const level = filter === 'all' ? undefined : filter;
      const d = await api.veille.listAlerts(level, 100);
      setAlerts(d.alerts);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filter]);

  const handleRunNow = async () => {
    setRunning(true);
    setRunResult(null);
    try {
      const r = await api.veille.runNow();
      setRunResult(`Exécutée : ${r.new_alerts} nouvelles alertes, ${r.critical} critiques sur ${r.items_analyzed} items analysés.`);
      load();
    } catch (e: any) {
      setRunResult(`Erreur : ${e.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Bell className="h-6 w-6" />
            Veille réglementaire Suisse romande
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Fedlex + cantons GE, VD, NE, FR, VS, JU · surveillance quotidienne automatique
          </p>
        </div>
        <Button onClick={handleRunNow} disabled={running} variant="outline">
          <RefreshCw className={`h-4 w-4 mr-2 ${running ? 'animate-spin' : ''}`} />
          {running ? 'Exécution...' : 'Lancer maintenant'}
        </Button>
      </div>

      {runResult && (
        <div className="rounded-md bg-blue-50 border border-blue-200 p-3 text-sm text-blue-900">
          {runResult}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Alertes détectées</CardTitle>
          <CardDescription>
            Les alertes CRITIQUES déclenchent un email immédiat aux admins. Les alertes IMPORTANT sont
            agrégées dans le rapport hebdomadaire du lundi matin.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 mb-4">
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toutes les alertes</SelectItem>
                <SelectItem value="CRITIQUE">Critiques uniquement</SelectItem>
                <SelectItem value="IMPORTANT">Importantes</SelectItem>
                <SelectItem value="INFO">Infos</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <div className="text-muted-foreground text-sm">Chargement...</div>
          ) : alerts.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucune alerte pour ce filtre.</p>
          ) : (
            <ul className="divide-y">
              {alerts.map((a) => (
                <li key={a.id} className="py-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <StatusBadge status={a.impact_level} />
                        <p className="text-xs text-muted-foreground">
                          {formatDateTime(a.detected_at)}
                        </p>
                      </div>
                      <p className="text-sm font-medium">{a.raw_data?.title || 'Alerte'}</p>
                      <p className="text-xs text-muted-foreground mt-1">{a.impact_summary}</p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {(a.raw_data?.domains || []).map((d: string) => (
                          <span key={d} className="text-[10px] px-1.5 py-0.5 rounded bg-muted">
                            {d}
                          </span>
                        ))}
                        {(a.raw_data?.jurisdiction || []).map((j: string) => (
                          <span key={j} className="text-[10px] px-1.5 py-0.5 rounded bg-muted">
                            {j}
                          </span>
                        ))}
                      </div>
                    </div>
                    {a.source_url && (
                      <a
                        href={a.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary hover:underline inline-flex items-center gap-1 shrink-0"
                      >
                        Source <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
