'use client';
import { useEffect } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log côté client pour Sentry/console
    console.error('Dashboard error:', error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-amber-100">
        <AlertTriangle className="h-7 w-7 text-amber-600" />
      </div>
      <h2 className="text-lg font-semibold">Quelque chose s'est mal passé</h2>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">
        Une erreur inattendue est survenue sur cette page. Vous pouvez réessayer ou
        revenir au tableau de bord. Aucune de vos données n'a été perdue.
      </p>
      <div className="mt-5 flex gap-3">
        <Button onClick={reset}>
          <RefreshCw className="mr-2 h-4 w-4" /> Réessayer
        </Button>
        <Button variant="outline" onClick={() => (window.location.href = '/dashboard')}>
          <Home className="mr-2 h-4 w-4" /> Tableau de bord
        </Button>
      </div>
    </div>
  );
}
