'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  FolderKanban, ListChecks, Clock, ArrowRight, Flame, Building, Layers,
  Building2, Shield, Bell, FileCheck2, MessageSquareWarning, Ruler, Zap,
  Sparkles, AlertCircle, Download, ChevronRight,
} from 'lucide-react';
import { api } from '@/lib/api';
import { TaskStatusBadge } from '@/components/ui/task-status';
import { Skeleton, SkeletonListItem } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { Banner } from '@/components/ui/banner';
import { TASK_TYPE_LABELS, formatDateTime } from '@/lib/utils';

// Estimation : jours économisés par type de tâche (moyenne marché BET romand)
const DAYS_SAVED_BY_TASK: Record<string, number> = {
  redaction_cctp: 3, chiffrage_dpgf: 2, chiffrage_dqe: 2,
  justificatif_sia_380_1: 1.5, note_calcul_sia_260_267: 2,
  idc_geneve_rapport: 1, idc_extraction_facture: 0.5,
  aeai_rapport: 1.5, aeai_checklist_generation: 0.5,
  descriptif_can_sia_451: 2, controle_reglementaire_geneve: 1,
  dossier_mise_enquete: 7, reponse_observations_autorite: 1.5,
  metres_automatiques_ifc: 1.5, simulation_energetique_rapide: 0.5,
  prebim_generation: 1, veille_romande: 0.2,
  compte_rendu_reunion: 0.2, coordination_inter_lots: 1,
};

// 6 modules phares avec description humaine
const MODULES = [
  {
    href: '/tasks/new?type=redaction_cctp',
    icon: FileCheck2,
    title: 'CCTP SIA 451',
    desc: 'Génère le descriptif technique structuré en 3 min',
    color: 'text-blue-600 bg-blue-50',
  },
  {
    href: '/thermique',
    icon: Flame,
    title: 'Justificatif SIA 380/1',
    desc: 'Depuis un IFC ou un modèle, vers ton Lesosai',
    color: 'text-orange-600 bg-orange-50',
  },
  {
    href: '/structure',
    icon: Building,
    title: 'Note SIA 260-267',
    desc: 'SAF pour Scia/RFEM + double-check M=qL²/8',
    color: 'text-slate-600 bg-slate-100',
  },
  {
    href: '/idc',
    icon: Building2,
    title: 'IDC Genève',
    desc: 'Extrait tes factures, calcule, pré-remplit le formulaire OCEN',
    color: 'text-emerald-600 bg-emerald-50',
  },
  {
    href: '/dossier-enquete',
    icon: FileCheck2,
    title: 'Dossier mise en enquête',
    desc: 'APA / APC avec mémoire justificatif et checklist pièces',
    color: 'text-purple-600 bg-purple-50',
  },
  {
    href: '/metres',
    icon: Ruler,
    title: 'Métrés automatiques',
    desc: 'IFC → SRE, volumes, DPGF pré-rempli par CFC',
    color: 'text-amber-600 bg-amber-50',
  },
];

export default function DashboardPage() {
  const [overview, setOverview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.dashboardOverview()
      .then((ov) => setOverview(ov))
      .catch((e: any) => setError(e?.message || 'Erreur de chargement'))
      .finally(() => setLoading(false));
  }, []);

  // Calcul jours économisés depuis les tâches complétées
  const daysSaved = (() => {
    if (!overview?.recent_tasks) return 0;
    return overview.recent_tasks
      .filter((t: any) => t.status === 'completed')
      .reduce((sum: number, t: any) => sum + (DAYS_SAVED_BY_TASK[t.task_type] || 0.5), 0);
  })();

  return (
    <div className="space-y-6">
      {/* Header de page */}
      <div>
        <h1 className="text-2xl font-semibold">Bonjour</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Vue d'ensemble de ton activité et des livrables récents.
        </p>
      </div>

      {error && (
        <Banner variant="error" title="Erreur de chargement">
          {error}
        </Banner>
      )}

      {/* KPIs humains */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard
          label="Projets actifs"
          value={loading ? null : (overview?.stats?.projects_count ?? 0)}
          icon={FolderKanban}
        />
        <KpiCard
          label="Tâches ce mois"
          value={loading ? null : (overview?.quota?.used ?? 0)}
          sublabel={loading ? '' : `/ ${overview?.quota?.limit ?? '∞'} inclus`}
          icon={ListChecks}
        />
        <KpiCard
          label="Temps économisé"
          value={loading ? null : `~${Math.round(daysSaved)} j`}
          sublabel="ingénieur équivalent"
          icon={Sparkles}
          accent="emerald"
        />
        <KpiCard
          label="Tâches en cours"
          value={loading ? null : (overview?.stats?.running_tasks ?? 0)}
          icon={Clock}
          accent="amber"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tâches récentes - élément le plus important, à gauche large */}
        <div className="lg:col-span-2">
          <SectionCard
            title="Tâches récentes"
            action={{ label: 'Voir tout', href: '/projects' }}
          >
            {loading ? (
              <div className="divide-y">
                {Array.from({ length: 4 }).map((_, i) => <SkeletonListItem key={i} />)}
              </div>
            ) : !overview?.recent_tasks?.length ? (
              <EmptyState
                icon={ListChecks}
                title="Pas encore de tâche"
                description="Crée ta première tâche pour voir l'agent à l'œuvre."
                action={{ label: 'Nouvelle tâche', href: '/tasks/new' }}
              />
            ) : (
              <div className="divide-y">
                {overview.recent_tasks.slice(0, 8).map((t: any) => (
                  <TaskRow key={t.id} task={t} />
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        {/* Quota + projets récents - colonne droite */}
        <div className="space-y-6">
          <SectionCard title="Quota du plan">
            {loading ? (
              <div className="space-y-2">
                <Skeleton className="h-2 w-full" />
                <Skeleton className="h-3 w-1/3" />
              </div>
            ) : (
              <QuotaBlock overview={overview} />
            )}
          </SectionCard>

          <SectionCard
            title="Projets récents"
            action={{ label: 'Tous', href: '/projects' }}
          >
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => <SkeletonListItem key={i} />)
            ) : !overview?.recent_projects?.length ? (
              <p className="text-sm text-muted-foreground py-3">Aucun projet.</p>
            ) : (
              <div className="space-y-1">
                {overview.recent_projects.slice(0, 5).map((p: any) => (
                  <Link
                    key={p.id}
                    href={`/projects/${p.id}`}
                    className="flex items-center justify-between py-2 px-2 -mx-2 rounded-md hover:bg-muted transition-colors group"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{p.name}</p>
                      <p className="text-xs text-muted-foreground truncate">
                        {p.canton ? `${p.canton} · ` : ''}{p.affectation || 'projet'}
                      </p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </Link>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      </div>

      {/* Accès rapide aux 6 modules */}
      <section>
        <h2 className="text-base font-medium mb-3">Accès rapide</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {MODULES.map((m) => (
            <Link
              key={m.href}
              href={m.href}
              className="group p-4 rounded-lg border bg-card hover:border-muted-foreground/30 hover:shadow-sm transition-all"
            >
              <div className={`inline-flex w-9 h-9 rounded-md ${m.color} items-center justify-center mb-3`}>
                <m.icon className="h-4 w-4" strokeWidth={1.8} />
              </div>
              <p className="font-medium text-sm mb-1">{m.title}</p>
              <p className="text-xs text-muted-foreground leading-relaxed">{m.desc}</p>
              <div className="mt-3 flex items-center gap-1 text-xs text-muted-foreground group-hover:text-foreground transition-colors">
                Ouvrir <ArrowRight className="h-3 w-3" />
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

function KpiCard({
  label, value, sublabel, icon: Icon, accent,
}: {
  label: string; value: any; sublabel?: string;
  icon: any; accent?: 'emerald' | 'amber' | 'red';
}) {
  const accentColor =
    accent === 'emerald' ? 'text-emerald-600' :
    accent === 'amber' ? 'text-amber-600' :
    accent === 'red' ? 'text-red-600' : 'text-foreground';

  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs text-muted-foreground font-medium">{label}</span>
        <Icon className="h-3.5 w-3.5 text-muted-foreground/60" strokeWidth={1.8} />
      </div>
      {value === null ? (
        <Skeleton className="h-7 w-16 mb-1" />
      ) : (
        <p className={`text-2xl font-semibold leading-none ${accentColor}`}>{value}</p>
      )}
      {sublabel && <p className="text-xs text-muted-foreground mt-1">{sublabel}</p>}
    </div>
  );
}

function SectionCard({
  title, action, children,
}: {
  title: string;
  action?: { label: string; href: string };
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border bg-card">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h2 className="text-sm font-medium">{title}</h2>
        {action && (
          <Link
            href={action.href}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
          >
            {action.label} <ArrowRight className="h-3 w-3" />
          </Link>
        )}
      </div>
      <div className="px-4 py-1">{children}</div>
    </section>
  );
}

function TaskRow({ task }: { task: any }) {
  const label = TASK_TYPE_LABELS[task.task_type] || task.task_type;
  const isDone = task.status === 'completed';

  return (
    <Link
      href={`/tasks/${task.id}`}
      className="flex items-center gap-3 py-3 hover:bg-muted/50 -mx-4 px-4 transition-colors"
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{label}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {formatDateTime(task.created_at)}
          {task.project_name && <> · {task.project_name}</>}
        </p>
      </div>
      <TaskStatusBadge status={task.status} />
      {isDone && task.result_url && (
        <a
          href={task.result_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="p-1.5 rounded-md hover:bg-background border text-muted-foreground hover:text-foreground transition-colors"
          title="Télécharger"
        >
          <Download className="h-3.5 w-3.5" />
        </a>
      )}
      <ChevronRight className="h-4 w-4 text-muted-foreground" />
    </Link>
  );
}

function QuotaBlock({ overview }: { overview: any }) {
  const used = overview?.quota?.used ?? 0;
  const limit = overview?.quota?.limit ?? 1;
  const pct = Math.min(100, Math.round((used / Math.max(limit, 1)) * 100));
  const isNearLimit = pct >= 80;

  return (
    <div className="py-2">
      <div className="flex items-end justify-between mb-2">
        <span className="text-2xl font-semibold leading-none">{used}</span>
        <span className="text-xs text-muted-foreground">/ {limit} ce mois</span>
      </div>
      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full transition-all ${
            isNearLimit ? 'bg-amber-500' : 'bg-primary'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {isNearLimit && (
        <p className="text-xs text-amber-700 mt-2 flex items-center gap-1">
          <AlertCircle className="h-3 w-3" />
          Quota bientôt atteint ({pct}%)
        </p>
      )}
      <Link
        href="/billing"
        className="text-xs text-muted-foreground hover:text-foreground mt-3 inline-block"
      >
        Plan {overview?.quota?.plan || 'starter'} · Gérer →
      </Link>
    </div>
  );
}
