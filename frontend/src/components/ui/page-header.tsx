import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

/**
 * En-tête de page homogène : titre + description explicative + zone d'action.
 * Donne à chaque écran un "à quoi ça sert" clair et cohérent.
 */
export function PageHeader({
  title,
  description,
  icon: Icon,
  back,
  children,
}: {
  title: string;
  description?: string;
  icon?: any;
  back?: { href: string; label: string };
  children?: React.ReactNode;
}) {
  return (
    <div className="space-y-3">
      {back && (
        <Link
          href={back.href}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> {back.label}
        </Link>
      )}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          {Icon && (
            <div className="hidden sm:flex w-10 h-10 rounded-lg bg-primary/10 text-primary items-center justify-center shrink-0">
              <Icon className="h-5 w-5" strokeWidth={1.8} />
            </div>
          )}
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            {description && (
              <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{description}</p>
            )}
          </div>
        </div>
        {children && <div className="shrink-0 flex items-center gap-2">{children}</div>}
      </div>
    </div>
  );
}
