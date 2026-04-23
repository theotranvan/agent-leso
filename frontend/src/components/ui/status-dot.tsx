import { cn } from '@/lib/utils';

export type ComplianceStatus = 'completed' | 'running' | 'queued' | 'failed' | 'not_started' | 'warning';

const STATUS_STYLES: Record<ComplianceStatus, { bg: string; ring: string; label: string }> = {
  completed: { bg: 'bg-emerald-500', ring: 'ring-emerald-500/20', label: 'Conforme' },
  running: { bg: 'bg-amber-500', ring: 'ring-amber-500/20', label: 'En cours' },
  queued: { bg: 'bg-amber-400', ring: 'ring-amber-400/20', label: 'En attente' },
  warning: { bg: 'bg-amber-500', ring: 'ring-amber-500/20', label: 'À vérifier' },
  failed: { bg: 'bg-red-500', ring: 'ring-red-500/20', label: 'Échec' },
  not_started: { bg: 'bg-muted-foreground/20', ring: 'ring-muted-foreground/10', label: 'Non commencé' },
};

export function StatusDot({
  status,
  size = 'sm',
  withRing = true,
  className,
}: {
  status: ComplianceStatus | string;
  size?: 'xs' | 'sm' | 'md';
  withRing?: boolean;
  className?: string;
}) {
  const mapped: ComplianceStatus = (STATUS_STYLES as any)[status] ? (status as ComplianceStatus) : 'not_started';
  const style = STATUS_STYLES[mapped];

  const sizes = {
    xs: 'h-2 w-2',
    sm: 'h-2.5 w-2.5',
    md: 'h-3 w-3',
  };

  return (
    <span
      className={cn(
        'inline-block rounded-full',
        sizes[size],
        style.bg,
        withRing && `ring-4 ${style.ring}`,
        className,
      )}
      title={style.label}
    />
  );
}

export function getStatusLabel(status: string): string {
  const mapped: ComplianceStatus = (STATUS_STYLES as any)[status] ? (status as ComplianceStatus) : 'not_started';
  return STATUS_STYLES[mapped].label;
}
