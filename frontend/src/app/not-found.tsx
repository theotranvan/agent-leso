import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="min-h-screen grid place-items-center px-6 bg-muted/30">
      <div className="text-center max-w-md">
        <div className="text-7xl font-bold text-muted-foreground/30 mb-4">404</div>
        <h1 className="text-2xl font-semibold mb-2">Page introuvable</h1>
        <p className="text-muted-foreground mb-8">
          L'URL demandée n'existe pas ou a été déplacée.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link href="/">
            <Button variant="outline">Accueil</Button>
          </Link>
          <Link href="/dashboard">
            <Button>Dashboard</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
