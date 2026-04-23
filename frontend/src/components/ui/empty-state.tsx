import type { LucideIcon } from 'lucide-react';
import Link from 'next/link';
import { Button } from './button';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
  secondaryAction?: {
    label: string;
    href?: string;
  };
}

export function EmptyState({ icon: Icon, title, description, action, secondaryAction }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6">
      {Icon && (
        <div className="w-12 h-12 rounded-full bg-muted grid place-items-center mb-4">
          <Icon className="h-6 w-6 text-muted-foreground" strokeWidth={1.5} />
        </div>
      )}
      <h3 className="text-base font-medium text-foreground mb-1.5">{title}</h3>
      {description && (
        <p className="text-sm text-muted-foreground max-w-md mb-5">{description}</p>
      )}
      {action && (
        <div className="flex items-center gap-2">
          {action.href ? (
            <Link href={action.href}>
              <Button>{action.label}</Button>
            </Link>
          ) : (
            <Button onClick={action.onClick}>{action.label}</Button>
          )}
          {secondaryAction?.href && (
            <Link href={secondaryAction.href}>
              <Button variant="ghost">{secondaryAction.label}</Button>
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
