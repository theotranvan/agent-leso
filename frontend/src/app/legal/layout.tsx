import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
            <ArrowLeft className="h-3.5 w-3.5" /> Accueil
          </Link>
          <nav className="flex items-center gap-5 text-sm text-muted-foreground">
            <Link href="/legal/cgu" className="hover:text-foreground">CGU</Link>
            <Link href="/legal/confidentialite" className="hover:text-foreground">Confidentialité</Link>
            <Link href="/legal/mentions-legales" className="hover:text-foreground">Mentions légales</Link>
          </nav>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-6 py-12">
        <article className="prose prose-sm prose-neutral max-w-none [&_h1]:text-2xl [&_h1]:font-semibold [&_h1]:mb-2 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mt-8 [&_h2]:mb-2 [&_p]:my-3 [&_p]:leading-relaxed [&_ul]:my-3 [&_ul]:list-disc [&_ul]:pl-6 [&_li]:my-1 [&_a]:text-primary [&_a]:underline">
          {children}
        </article>
      </main>
      <footer className="border-t">
        <div className="max-w-3xl mx-auto px-6 py-6 text-xs text-muted-foreground">
          © {new Date().getFullYear()} LESO · Suisse romande
        </div>
      </footer>
    </div>
  );
}
