'use client';
import { STATUS_COLORS } from '@/lib/ch';
import { cn } from '@/lib/utils';

interface Props {
  status: string;
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label, className }: Props) {
  const colorClass = STATUS_COLORS[status] || 'bg-slate-100 text-slate-700';
  return (
    <span className={cn('inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium', colorClass, className)}>
      {label || status}
    </span>
  );
}
