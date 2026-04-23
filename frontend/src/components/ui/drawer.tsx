'use client';
import { useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: 'sm' | 'md' | 'lg';
}

export function Drawer({ open, onClose, title, subtitle, children, footer, width = 'md' }: DrawerProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handler);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;

  const widths = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl' };

  return (
    <>
      <div
        className="fixed inset-0 bg-black/30 backdrop-blur-[2px] z-40 animate-in fade-in duration-200"
        onClick={onClose}
      />
      <aside
        className={cn(
          'fixed right-0 top-0 bottom-0 z-50 w-full bg-background border-l shadow-2xl flex flex-col',
          'animate-in slide-in-from-right duration-200',
          widths[width],
        )}
      >
        {(title || subtitle) && (
          <div className="flex items-start justify-between p-5 border-b">
            <div>
              {title && <h3 className="font-medium text-base">{title}</h3>}
              {subtitle && <p className="text-sm text-muted-foreground mt-0.5">{subtitle}</p>}
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md hover:bg-muted transition-colors"
              aria-label="Fermer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
        {footer && <div className="border-t p-4 bg-muted/30">{footer}</div>}
      </aside>
    </>
  );
}
