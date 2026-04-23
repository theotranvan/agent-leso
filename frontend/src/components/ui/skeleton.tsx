import { cn } from '@/lib/utils';

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton rounded-md', className)} />;
}

/** Skeleton pour une ligne de tableau / liste */
export function SkeletonRow({ cols = 3 }: { cols?: number }) {
  return (
    <div className="flex items-center gap-3 py-3 border-b">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} className={cn('h-4', i === 0 ? 'w-1/3' : 'w-1/4')} />
      ))}
    </div>
  );
}

/** Skeleton pour une card */
export function SkeletonCard() {
  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="h-3 w-3/4" />
      <Skeleton className="h-3 w-1/3" />
    </div>
  );
}

/** Skeleton pour une ligne de liste (header + subtitle) */
export function SkeletonListItem() {
  return (
    <div className="py-3 border-b space-y-2">
      <Skeleton className="h-4 w-2/5" />
      <Skeleton className="h-3 w-1/4" />
    </div>
  );
}
