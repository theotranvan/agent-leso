'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { MapPin, ClipboardCheck, CalendarClock, FolderKanban } from 'lucide-react';
import { api } from '@/lib/api';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';

const PHASE_COLORS: Record<string, string> = {
  avant_projet: '#2E75B6',
  projet_ouvrage: '#1D9E75',
  autorisation: '#BA7517',
  appel_offres: '#7F77DD',
  execution: '#D85A30',
  cloture: '#0F6E56',
};

export default function BoardPage() {
  const router = useRouter();
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = () => {
    setLoading(true); setError(null);
    api.projectsBoard()
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="flex gap-4 overflow-x-auto">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-64 w-72 flex-shrink-0" />)}
        </div>
      </div>
    );
  }

  if (error) return <ErrorState error={error} onRetry={load} />;

  if (!data || data.total_projects === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold tracking-tight">Mes affaires</h1>
        <EmptyState icon={FolderKanban} title="Aucune affaire active"
          description="Créez votre première affaire pour la voir apparaître ici, organisée par phase." />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Mes affaires</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {data.total_projects} affaire(s) active(s)
            {data.total_to_validate > 0 && ` · ${data.total_to_validate} document(s) à valider`}
          </p>
        </div>
      </div>

      {/* Kanban scrollable horizontalement */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {data.columns.map((col: any) => {
          const color = PHASE_COLORS[col.phase_key] || '#888780';
          return (
            <div key={col.phase_key} className="w-72 flex-shrink-0">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
                  <span className="text-sm font-medium">{col.label}</span>
                  {col.sia_code !== '—' && (
                    <span className="text-xs text-muted-foreground">SIA {col.sia_code}</span>
                  )}
                </div>
                <span className="rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
                  {col.count}
                </span>
              </div>

              <div className="space-y-2">
                {col.projects.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border/60 p-4 text-center text-xs text-muted-foreground">
                    Aucune affaire
                  </div>
                ) : (
                  col.projects.map((p: any) => (
                    <button
                      key={p.id}
                      onClick={() => router.push(`/projects/${p.id}`)}
                      className="w-full rounded-lg border border-border/60 bg-background p-3 text-left transition hover:border-border hover:shadow-sm"
                      style={{ borderLeftWidth: 3, borderLeftColor: color }}
                    >
                      <div className="text-sm font-medium">{p.name}</div>
                      {p.commune && (
                        <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                          <MapPin className="h-3 w-3" /> {p.commune} {p.canton && `(${p.canton})`}
                        </div>
                      )}
                      {(p.labels || []).length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {p.labels.slice(0, 3).map((l: string) => (
                            <span key={l} className="rounded bg-secondary px-1.5 py-0.5 text-xs text-muted-foreground">{l}</span>
                          ))}
                        </div>
                      )}
                      <div className="mt-2 flex items-center gap-3 text-xs">
                        {p.to_validate > 0 && (
                          <span className="flex items-center gap-1 text-amber-600">
                            <ClipboardCheck className="h-3 w-3" /> {p.to_validate} à valider
                          </span>
                        )}
                        {p.next_deadline && (
                          <span className="flex items-center gap-1 text-muted-foreground">
                            <CalendarClock className="h-3 w-3" /> {p.next_deadline.label}
                          </span>
                        )}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
