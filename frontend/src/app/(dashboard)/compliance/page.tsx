'use client';
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  ShieldCheck, Flame, Building, Building2, Shield, FileCheck2, MessageSquareWarning,
  Search, AlertCircle, ChevronRight, Download, ArrowUpRight,
} from 'lucide-react';
import { api } from '@/lib/api';
import { StatusDot, getStatusLabel, ComplianceStatus } from '@/components/ui/status-dot';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { Banner } from '@/components/ui/banner';
import { Drawer } from '@/components/ui/drawer';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { formatDate } from '@/lib/utils';

type DimensionKey = 'thermique' | 'structure' | 'idc' | 'aeai' | 'dossier_enquete' | 'observations';

const DIMENSIONS: { key: DimensionKey; label: string; icon: any; short: string }[] = [
  { key: 'thermique', label: 'Thermique SIA 380/1', icon: Flame, short: 'Thermique' },
  { key: 'structure', label: 'Structure SIA 260-267', icon: Building, short: 'Structure' },
  { key: 'idc', label: 'IDC Genève', icon: Building2, short: 'IDC' },
  { key: 'aeai', label: 'AEAI (incendie)', icon: Shield, short: 'AEAI' },
  { key: 'dossier_enquete', label: 'Dossier enquête', icon: FileCheck2, short: 'Dossier' },
  { key: 'observations', label: 'Observations', icon: MessageSquareWarning, short: 'Obs.' },
];

type ProjectRow = {
  project_id: string; project_name: string; canton?: string;
  affectation?: string; phase_sia?: string; sre_m2?: number;
  thermique: any; structure: any; idc: any; aeai: any;
  dossier_enquete: any; observations: any; last_activity_at?: string;
};

export default function CompliancePage() {
  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [filterAlerts, setFilterAlerts] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selected, setSelected] = useState<{ project: ProjectRow; dim: DimensionKey } | null>(null);

  useEffect(() => {
    api.dashboard.compliance()
      .then((r) => setProjects(r.projects as ProjectRow[]))
      .catch((e: any) => setError(e?.message || 'Erreur'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    let result = projects;
    if (query) {
      const q = query.toLowerCase();
      result = result.filter((p) =>
        p.project_name.toLowerCase().includes(q) ||
        (p.canton || '').toLowerCase().includes(q) ||
        (p.affectation || '').toLowerCase().includes(q)
      );
    }
    if (filterAlerts) {
      result = result.filter((p) => hasAlert(p));
    }
    return result;
  }, [projects, query, filterAlerts]);

  const alertCount = projects.filter(hasAlert).length;

  const openDrawer = (project: ProjectRow, dim: DimensionKey) => {
    setSelected({ project, dim });
    setDrawerOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <h1 className="text-2xl font-semibold">Conformité multi-projets</h1>
          </div>
          <p className="text-sm text-muted-foreground">
            État réglementaire par projet — thermique, structure, IDC, AEAI, dossiers et observations.
          </p>
        </div>
      </div>

      {error && <Banner variant="error">{error}</Banner>}

      {/* Stats + filtres */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Filtrer par nom, canton, affectation…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full h-9 pl-9 pr-3 rounded-md border bg-card text-sm focus-ring"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setFilterAlerts(false)}
            className={`px-3 h-9 rounded-md text-sm font-medium transition-colors ${
              !filterAlerts ? 'bg-primary text-primary-foreground' : 'bg-card border hover:bg-muted'
            }`}
          >
            Tout ({projects.length})
          </button>
          <button
            onClick={() => setFilterAlerts(true)}
            className={`px-3 h-9 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5 ${
              filterAlerts ? 'bg-amber-500 text-white' : 'bg-card border hover:bg-muted'
            }`}
          >
            <AlertCircle className="h-3.5 w-3.5" /> Alertes ({alertCount})
          </button>
        </div>
      </div>

      {/* Tableau */}
      {loading ? (
        <ComplianceTableSkeleton />
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border bg-card">
          <EmptyState
            icon={ShieldCheck}
            title={query || filterAlerts ? 'Aucun projet correspondant' : 'Aucun projet actif'}
            description={
              query || filterAlerts
                ? 'Ajuste tes filtres pour voir plus de résultats.'
                : 'Crée ton premier projet pour voir le tableau de bord conformité.'
            }
            action={!query && !filterAlerts ? { label: 'Créer un projet', href: '/projects' } : undefined}
          />
        </div>
      ) : (
        <div className="rounded-lg border bg-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-xs">
                <tr>
                  <th className="text-left p-3 font-medium w-[28%]">Projet</th>
                  {DIMENSIONS.map((d) => (
                    <th key={d.key} className="text-center p-3 font-medium">
                      <div className="flex flex-col items-center gap-1">
                        <d.icon className="h-3.5 w-3.5 text-muted-foreground" />
                        <span>{d.short}</span>
                      </div>
                    </th>
                  ))}
                  <th className="text-right p-3 font-medium whitespace-nowrap">Dernière</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p) => (
                  <tr key={p.project_id} className="border-t hover:bg-muted/20 transition-colors">
                    <td className="p-3">
                      <Link href={`/projects/${p.project_id}`} className="group">
                        <p className="font-medium truncate group-hover:underline">{p.project_name}</p>
                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                          {p.canton && <Badge variant="outline" className="text-[10px] mr-1 h-4 px-1">{p.canton}</Badge>}
                          {p.affectation}
                          {p.sre_m2 && <> · {p.sre_m2} m²</>}
                        </p>
                      </Link>
                    </td>
                    {DIMENSIONS.map((d) => {
                      const status = getDimensionStatus(p, d.key);
                      return (
                        <td key={d.key} className="text-center p-3">
                          <button
                            onClick={() => openDrawer(p, d.key)}
                            className="inline-flex items-center justify-center w-8 h-8 rounded-md hover:bg-muted transition-colors"
                            aria-label={`${d.label}: ${getStatusLabel(status)}`}
                          >
                            <StatusDot status={status} size="sm" />
                          </button>
                        </td>
                      );
                    })}
                    <td className="text-right p-3 text-xs text-muted-foreground whitespace-nowrap">
                      {p.last_activity_at ? formatDate(p.last_activity_at) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Légende */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5"><StatusDot status="completed" size="xs" withRing={false} /> Conforme</div>
        <div className="flex items-center gap-1.5"><StatusDot status="running" size="xs" withRing={false} /> En cours</div>
        <div className="flex items-center gap-1.5"><StatusDot status="failed" size="xs" withRing={false} /> Échec</div>
        <div className="flex items-center gap-1.5"><StatusDot status="not_started" size="xs" withRing={false} /> Non commencé</div>
      </div>

      {/* Drawer détail */}
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={selected ? DIMENSIONS.find((d) => d.key === selected.dim)?.label : undefined}
        subtitle={selected?.project.project_name}
      >
        {selected && <DimensionDetail project={selected.project} dim={selected.dim} />}
      </Drawer>
    </div>
  );
}

function hasAlert(p: ProjectRow): boolean {
  if (p.thermique?.status === 'failed') return true;
  if (p.structure?.status === 'failed') return true;
  if (p.idc?.status === 'failed') return true;
  if (p.observations?.nb_pending > 0) return true;
  return false;
}

function getDimensionStatus(p: ProjectRow, dim: DimensionKey): ComplianceStatus {
  if (dim === 'observations') {
    if (p.observations?.nb_pending > 0) return 'warning';
    if (p.observations?.nb_total > 0) return 'completed';
    return 'not_started';
  }
  if (dim === 'aeai') {
    const nb = p.aeai?.nb_checklists ?? 0;
    const validated = p.aeai?.nb_validated ?? 0;
    if (nb === 0) return 'not_started';
    if (validated === nb) return 'completed';
    if (validated > 0) return 'running';
    return 'warning';
  }
  const data = (p as any)[dim];
  if (!data) return 'not_started';
  const status = data.status || 'not_started';
  if (status === 'non_calcule' || status === 'non_commence') return 'not_started';
  return status as ComplianceStatus;
}

function DimensionDetail({ project, dim }: { project: ProjectRow; dim: DimensionKey }) {
  const data = (project as any)[dim] || {};
  const status = getDimensionStatus(project, dim);
  const dimInfo = DIMENSIONS.find((d) => d.key === dim)!;

  const moduleLink: Record<DimensionKey, string> = {
    thermique: '/thermique',
    structure: '/structure',
    idc: '/idc',
    aeai: '/aeai',
    dossier_enquete: '/dossier-enquete',
    observations: '/observations',
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 p-4 rounded-lg bg-muted/40">
        <div className="w-10 h-10 rounded-md bg-card grid place-items-center border">
          <dimInfo.icon className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium">Statut actuel</p>
          <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
            <StatusDot status={status} size="xs" withRing={false} />
            {getStatusLabel(status)}
          </p>
        </div>
      </div>

      {/* Infos détaillées selon dimension */}
      {dim === 'observations' && (
        <InfoBlock>
          <Row label="Total réponses générées" value={project.observations?.nb_total ?? 0} />
          <Row label="En cours" value={project.observations?.nb_pending ?? 0}
            warning={project.observations?.nb_pending > 0} />
        </InfoBlock>
      )}

      {dim === 'aeai' && (
        <InfoBlock>
          <Row label="Checklists créées" value={project.aeai?.nb_checklists ?? 0} />
          <Row label="Checklists validées" value={project.aeai?.nb_validated ?? 0} />
          {project.aeai?.last_update && (
            <Row label="Dernière mise à jour" value={formatDate(project.aeai.last_update)} />
          )}
        </InfoBlock>
      )}

      {['thermique', 'structure', 'idc', 'dossier_enquete'].includes(dim) && (
        <InfoBlock>
          <Row label="Statut de la tâche" value={data.status || 'non calculé'} />
          {data.last_date && <Row label="Dernière date" value={formatDate(data.last_date)} />}
          {data.preview && (
            <div className="pt-2">
              <p className="text-xs text-muted-foreground mb-1">Aperçu du résultat</p>
              <div className="p-3 bg-muted/50 rounded-md text-xs font-mono leading-relaxed">
                {data.preview}
              </div>
            </div>
          )}
        </InfoBlock>
      )}

      <div className="flex items-center gap-2 pt-2">
        <Link href={`/projects/${project.project_id}`} className="flex-1">
          <Button variant="outline" className="w-full gap-2">
            Voir le projet <ArrowUpRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
        <Link href={moduleLink[dim]}>
          <Button className="gap-2">
            Module {dimInfo.short.toLowerCase()}
          </Button>
        </Link>
      </div>
    </div>
  );
}

function InfoBlock({ children }: { children: React.ReactNode }) {
  return <div className="rounded-lg border divide-y">{children}</div>;
}

function Row({ label, value, warning }: { label: string; value: any; warning?: boolean }) {
  return (
    <div className="flex items-center justify-between px-3 py-2.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={`font-medium ${warning ? 'text-amber-700' : ''}`}>{value}</span>
    </div>
  );
}

function ComplianceTableSkeleton() {
  return (
    <div className="rounded-lg border bg-card">
      <div className="p-3 border-b bg-muted/40">
        <Skeleton className="h-4 w-40" />
      </div>
      <div className="divide-y">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 p-3">
            <div className="w-[28%] space-y-1.5">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
            <div className="flex-1 flex gap-4 justify-around">
              {Array.from({ length: 6 }).map((_, j) => <Skeleton key={j} className="h-2.5 w-2.5 rounded-full" />)}
            </div>
            <Skeleton className="h-3 w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}
