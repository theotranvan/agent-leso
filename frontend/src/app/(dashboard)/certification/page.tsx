'use client';
import { useEffect, useState } from 'react';
import { Award, Copy, Check, ExternalLink, Lock } from 'lucide-react';
import { api } from '@/lib/api';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';

const LEVEL_COLOR: Record<string, string> = {
  Or: '#C9A227', Argent: '#8E9099', Bronze: '#A97142',
};

export default function CertificationPage() {
  const [cert, setCert] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [copied, setCopied] = useState(false);

  const load = () => {
    setLoading(true); setError(null);
    api.certificationStatus().then(setCert).catch(setError).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const copyEmbed = () => {
    if (cert?.embed_html) {
      navigator.clipboard.writeText(cert.embed_html);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-48 w-full" /></div>;
  if (error) return <ErrorState error={error} onRetry={load} />;
  if (!cert) return null;

  const color = cert.level ? LEVEL_COLOR[cert.level] : '#1B3A5C';

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Certification bureau</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Valorisez votre usage de LESO auprès de vos clients et maîtres d'ouvrage.
        </p>
      </div>

      {cert.eligible ? (
        <>
          {/* Badge actif */}
          <div className="rounded-xl border border-border/60 p-6 text-center"
            style={{ borderTopWidth: 4, borderTopColor: color }}>
            <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full"
              style={{ background: `${color}1a` }}>
              <Award className="h-7 w-7" style={{ color }} />
            </div>
            <h2 className="text-lg font-semibold">{cert.label}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {cert.approved_docs} documents validés · {cert.approval_rate}% de taux d'approbation
            </p>
            <a href={cert.verify_url} target="_blank" rel="noopener"
              className="mt-3 inline-flex items-center gap-1 text-sm text-primary hover:underline">
              Voir la page publique <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>

          {/* Code d'intégration */}
          <div className="rounded-lg border border-border/60 p-5">
            <h3 className="text-sm font-semibold">Afficher le badge sur votre site</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Copiez ce code et collez-le sur votre site web. Chaque visiteur pourra
              vérifier l'authenticité de votre certification.
            </p>
            <div className="mt-3 rounded-md bg-secondary/50 p-3">
              <code className="block overflow-x-auto whitespace-pre text-xs text-muted-foreground">
                {cert.embed_html}
              </code>
            </div>
            <button onClick={copyEmbed}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-secondary">
              {copied ? <><Check className="h-3.5 w-3.5 text-green-600" /> Copié</> : <><Copy className="h-3.5 w-3.5" /> Copier le code</>}
            </button>
          </div>
        </>
      ) : (
        /* Pas encore certifié — montrer la progression */
        <div className="rounded-xl border border-border/60 p-6">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary">
              <Lock className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <h2 className="font-medium">Certification pas encore active</h2>
              <p className="text-sm text-muted-foreground">
                Continuez à produire et valider des documents pour l'obtenir.
              </p>
            </div>
          </div>

          <div className="space-y-3 rounded-lg bg-secondary/30 p-4 text-sm">
            <div className="flex items-center justify-between">
              <span>Documents validés</span>
              <span className="font-medium">
                {cert.approved_docs} / {cert.criteria.min_approved}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-border/60">
              <div className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${Math.min(100, (cert.approved_docs / cert.criteria.min_approved) * 100)}%` }} />
            </div>
            <div className="flex items-center justify-between">
              <span>Taux d'approbation</span>
              <span className="font-medium">
                {cert.approval_rate}% <span className="text-muted-foreground">(min. {cert.criteria.min_approval_rate}%)</span>
              </span>
            </div>
          </div>

          <p className="mt-4 text-xs text-muted-foreground">
            Trois niveaux : Bronze (10 docs), Argent (40 docs), Or (100 docs).
          </p>
        </div>
      )}
    </div>
  );
}
