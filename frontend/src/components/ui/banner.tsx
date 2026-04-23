import { AlertCircle, Info, CheckCircle2, AlertTriangle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

type Variant = 'error' | 'warning' | 'info' | 'success';

const VARIANT_STYLES: Record<Variant, { bg: string; text: string; border: string; icon: typeof AlertCircle }> = {
  error: { bg: 'bg-red-50', text: 'text-red-800', border: 'border-red-200', icon: AlertCircle },
  warning: { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200', icon: AlertTriangle },
  info: { bg: 'bg-blue-50', text: 'text-blue-800', border: 'border-blue-200', icon: Info },
  success: { bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200', icon: CheckCircle2 },
};

export function Banner({
  variant = 'error',
  title,
  children,
  onDismiss,
  className,
}: {
  variant?: Variant;
  title?: string;
  children: React.ReactNode;
  onDismiss?: () => void;
  className?: string;
}) {
  const style = VARIANT_STYLES[variant];
  const Icon = style.icon;
  return (
    <div className={cn('flex items-start gap-3 p-3 rounded-md border text-sm', style.bg, style.border, style.text, className)}>
      <Icon className="h-4 w-4 mt-0.5 shrink-0" />
      <div className="flex-1">
        {title && <p className="font-medium mb-0.5">{title}</p>}
        <div className="leading-relaxed">{children}</div>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="shrink-0 opacity-60 hover:opacity-100 transition-opacity"
          aria-label="Fermer"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
