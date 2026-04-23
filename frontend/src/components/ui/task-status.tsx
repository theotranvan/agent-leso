import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

type TaskStatus = 'queued' | 'running' | 'completed' | 'failed' | string;

const VARIANTS: Record<string, { bg: string; text: string; label: string }> = {
  queued: { bg: 'bg-amber-50', text: 'text-amber-800', label: 'En attente' },
  running: { bg: 'bg-blue-50', text: 'text-blue-800', label: 'En cours' },
  completed: { bg: 'bg-emerald-50', text: 'text-emerald-800', label: 'Terminé' },
  failed: { bg: 'bg-red-50', text: 'text-red-800', label: 'Erreur' },
  draft: { bg: 'bg-muted', text: 'text-muted-foreground', label: 'Brouillon' },
  validated: { bg: 'bg-emerald-50', text: 'text-emerald-800', label: 'Validé' },
  ready: { bg: 'bg-blue-50', text: 'text-blue-800', label: 'Prêt' },
};

export function TaskStatusBadge({ status, className }: { status: TaskStatus; className?: string }) {
  const v = VARIANTS[status] || { bg: 'bg-muted', text: 'text-muted-foreground', label: status };
  const showSpinner = status === 'running';
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
        v.bg, v.text, className,
      )}
    >
      {showSpinner && <Loader2 className="h-3 w-3 animate-spin" />}
      {v.label}
    </span>
  );
}
