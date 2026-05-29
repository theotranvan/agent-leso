'use client';
import { AlertCircle, RefreshCw, WifiOff, Lock, FileQuestion } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorStateProps {
  error?: unknown;
  title?: string;
  onRetry?: () => void;
  compact?: boolean;
}

function resolveError(error: unknown): { message: string; status?: number } {
  if (error && typeof error === 'object') {
    const e = error as any;
    if (e.userMessage) return { message: e.userMessage, status: e.status };
    if (e.message) return { message: e.message, status: e.status };
  }
  if (typeof error === 'string') return { message: error };
  return { message: 'Une erreur est survenue.' };
}

function pickIcon(status?: number) {
  if (status === 401 || status === 403) return Lock;
  if (status === 404) return FileQuestion;
  if (status === undefined) return WifiOff;
  return AlertCircle;
}

export function ErrorState({ error, title, onRetry, compact }: ErrorStateProps) {
  const { message, status } = resolveError(error);
  const Icon = pickIcon(status);
  const heading = title || (status === 401 ? 'Session expirée' : 'Une erreur est survenue');

  if (compact) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-3">
        <Icon className="h-4 w-4 flex-shrink-0 text-red-600" />
        <span className="flex-1 text-sm text-red-800">{message}</span>
        {onRetry && (
          <button onClick={onRetry} className="flex items-center gap-1 text-sm font-medium text-red-700 hover:underline">
            <RefreshCw className="h-3.5 w-3.5" /> Réessayer
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-border/60 bg-secondary/20 px-6 py-12 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
        <Icon className="h-6 w-6 text-red-600" />
      </div>
      <h3 className="text-base font-medium">{heading}</h3>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">{message}</p>
      {status === 401 ? (
        <Button className="mt-4" onClick={() => (window.location.href = '/login')}>
          Se reconnecter
        </Button>
      ) : onRetry ? (
        <Button variant="outline" className="mt-4" onClick={onRetry}>
          <RefreshCw className="mr-2 h-4 w-4" /> Réessayer
        </Button>
      ) : null}
    </div>
  );
}
