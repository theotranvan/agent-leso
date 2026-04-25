'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Gauge, Zap, CreditCard, TrendingUp, Loader2, AlertCircle, Check,
  Package, Sparkles, ArrowLeft,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Banner } from '@/components/ui/banner';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDateTime } from '@/lib/utils';

type Usage = {
  plan: string;
  month: string;
  tokens_used: number;
  tokens_limit: number;
  tokens_pack_remaining: number;
  tokens_total_available: number;
  used_pct: number;
  cost_chf_estimated: number;
  by_model: Record<string, { tokens: number; cost_chf: number; calls: number }>;
  credit_packs: any[];
  pack_info: { tokens_per_pack: number; price_chf_per_pack: number };
};

const MODEL_LABELS: Record<string, { name: string; color: string }> = {
  'claude-opus-4-6': { name: 'Opus', color: 'bg-purple-500' },
  'claude-sonnet-4-6': { name: 'Sonnet', color: 'bg-blue-500' },
  'claude-haiku-4-5-20251001': { name: 'Haiku', color: 'bg-emerald-500' },
};

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return n.toLocaleString('fr-CH');
}

export default function BillingUsagePage() {
  const [usage, setUsage] = useState<Usage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [purchasing, setPurchasing] = useState(false);
  const [packQuantity, setPackQuantity] = useState(1);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/billing/usage`, {
        headers: await (api as any).authHeaders?.() || {},
        credentials: 'include',
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setUsage(await r.json());
    } catch (e: any) {
      // Fallback : appel via api helper existant
      try {
        const res = await (api as any).billing?.getUsage?.();
        if (res) setUsage(res);
        else throw new Error('Endpoint /billing/usage non disponible');
      } catch (err: any) {
        setError(err?.message || 'Erreur de chargement');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const params = new URLSearchParams(window.location.search);
    if (params.get('pack_purchased') === '1') {
      setSuccessMessage('Pack ajouté à ton compte. La consommation reflète désormais les nouveaux crédits.');
      window.history.replaceState({}, '', '/settings/billing');
    }
  }, []);

  const handlePurchase = async () => {
    setPurchasing(true);
    setError(null);
    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/billing/credit-pack/checkout`, {
        method: 'POST',
        headers: {
          ...(await (api as any).authHeaders?.() || {}),
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ quantity: packQuantity }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const { checkout_url } = await r.json();
      window.location.href = checkout_url;
    } catch (e: any) {
      setError(e?.message || "Échec ouverture du paiement");
      setPurchasing(false);
    }
  };

  if (loading) return <BillingSkeleton />;

  if (error && !usage) {
    return (
      <div className="space-y-4">
        <Link href="/settings" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
          <ArrowLeft className="h-3.5 w-3.5" /> Paramètres
        </Link>
        <Banner variant="error">{error}</Banner>
      </div>
    );
  }

  if (!usage) return null;

  const quotaColor =
    usage.used_pct >= 100 ? 'bg-red-500' :
    usage.used_pct >= 80 ? 'bg-amber-500' : 'bg-emerald-500';

  const totalPackTokens = (usage.credit_packs || []).reduce((sum, p) => sum + (p.tokens_granted || 0), 0);

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <Link href="/settings" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1 mb-3">
          <ArrowLeft className="h-3.5 w-3.5" /> Paramètres
        </Link>
        <div className="flex items-center gap-2.5 mb-1">
          <Gauge className="h-5 w-5 text-primary" />
          <h1 className="text-2xl font-semibold">Consommation &amp; facturation</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Quota tokens du plan actuel et historique d'achats de packs additionnels.
        </p>
      </div>

      {successMessage && (
        <Banner variant="success" onDismiss={() => setSuccessMessage(null)}>
          {successMessage}
        </Banner>
      )}
      {error && <Banner variant="error" onDismiss={() => setError(null)}>{error}</Banner>}

      {/* Jauge principale */}
      <section className="rounded-lg border bg-card p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
              Quota mensuel — {usage.month}
            </p>
            <h2 className="text-3xl font-semibold">
              {formatTokens(usage.tokens_used)} <span className="text-muted-foreground text-xl">/ {formatTokens(usage.tokens_limit)} tokens</span>
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Plan <span className="font-medium capitalize">{usage.plan}</span> · {usage.used_pct}% consommé
            </p>
          </div>
          {usage.used_pct >= 80 && (
            <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium ${
              usage.used_pct >= 100 ? 'bg-red-50 text-red-800' : 'bg-amber-50 text-amber-800'
            }`}>
              <AlertCircle className="h-3.5 w-3.5" />
              {usage.used_pct >= 100 ? 'Quota dépassé' : 'Bientôt atteint'}
            </div>
          )}
        </div>

        <div className="h-3 bg-muted rounded-full overflow-hidden">
          <div
            className={`h-full transition-all ${quotaColor}`}
            style={{ width: `${Math.min(100, usage.used_pct)}%` }}
          />
        </div>

        <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
          <span>Reset au 1er du mois prochain</span>
          <span>Coût estimé : <strong className="text-foreground">{usage.cost_chf_estimated.toFixed(2)} CHF</strong></span>
        </div>
      </section>

      {/* Packs restants + bouton achat */}
      <section className="rounded-lg border bg-card p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Package className="h-4 w-4 text-muted-foreground" />
              <h2 className="font-medium">Tokens additionnels (credit packs)</h2>
            </div>
            <p className="text-sm text-muted-foreground">
              Consommés automatiquement après épuisement du quota mensuel.
            </p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-semibold">{formatTokens(usage.tokens_pack_remaining)}</p>
            <p className="text-xs text-muted-foreground">disponibles</p>
          </div>
        </div>

        <div className="rounded-md bg-muted/50 p-4 border">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="font-medium text-sm">Pack de {formatTokens(usage.pack_info.tokens_per_pack)} tokens</p>
              <p className="text-xs text-muted-foreground">Sans date d'expiration · Facturation unique</p>
            </div>
            <p className="text-lg font-semibold">{usage.pack_info.price_chf_per_pack} CHF</p>
          </div>

          <div className="flex items-center gap-2 mb-3">
            <label className="text-xs text-muted-foreground">Quantité :</label>
            <div className="inline-flex items-center border rounded-md">
              <button
                onClick={() => setPackQuantity(Math.max(1, packQuantity - 1))}
                className="px-2 py-0.5 hover:bg-muted transition-colors"
                disabled={packQuantity <= 1}
              >−</button>
              <span className="w-8 text-center text-sm font-medium">{packQuantity}</span>
              <button
                onClick={() => setPackQuantity(Math.min(20, packQuantity + 1))}
                className="px-2 py-0.5 hover:bg-muted transition-colors"
                disabled={packQuantity >= 20}
              >+</button>
            </div>
            <span className="text-xs text-muted-foreground ml-2">
              = {formatTokens(usage.pack_info.tokens_per_pack * packQuantity)} tokens pour {usage.pack_info.price_chf_per_pack * packQuantity} CHF
            </span>
          </div>

          <Button onClick={handlePurchase} disabled={purchasing} className="gap-2 w-full sm:w-auto">
            {purchasing && <Loader2 className="h-4 w-4 animate-spin" />}
            <CreditCard className="h-4 w-4" />
            {purchasing ? 'Ouverture du paiement…' : `Acheter ${packQuantity > 1 ? `${packQuantity} packs` : 'un pack'}`}
          </Button>
        </div>

        {/* Historique des packs */}
        {usage.credit_packs && usage.credit_packs.length > 0 && (
          <div className="mt-5">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">Historique</p>
            <div className="border rounded-md divide-y">
              {usage.credit_packs.slice(0, 5).map((p) => (
                <div key={p.id} className="flex items-center justify-between px-3 py-2 text-sm">
                  <div>
                    <p className="font-medium">{formatTokens(p.tokens_granted)} tokens</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDateTime(p.purchased_at)}
                      {p.tokens_remaining > 0 && <> · {formatTokens(p.tokens_remaining)} restants</>}
                    </p>
                  </div>
                  <span className="text-xs font-medium">{p.price_chf_paid} CHF</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Répartition par modèle */}
      {Object.keys(usage.by_model).length > 0 && (
        <section className="rounded-lg border bg-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
            <h2 className="font-medium">Répartition par modèle ce mois</h2>
          </div>
          <div className="space-y-3">
            {Object.entries(usage.by_model)
              .sort((a, b) => b[1].tokens - a[1].tokens)
              .map(([model, data]) => {
                const info = MODEL_LABELS[model] || { name: model, color: 'bg-gray-500' };
                const pctOfUsed = usage.tokens_used ? (data.tokens / usage.tokens_used) * 100 : 0;
                return (
                  <div key={model}>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${info.color}`} />
                        <span className="text-sm font-medium">{info.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {data.calls} appel{data.calls > 1 ? 's' : ''}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-medium">{formatTokens(data.tokens)}</span>
                        <span className="text-xs text-muted-foreground ml-2">
                          {data.cost_chf.toFixed(2)} CHF
                        </span>
                      </div>
                    </div>
                    <div className="h-1 bg-muted rounded-full overflow-hidden">
                      <div className={`h-full ${info.color}`} style={{ width: `${pctOfUsed}%` }} />
                    </div>
                  </div>
                );
              })}
          </div>
        </section>
      )}

      <div className="text-xs text-muted-foreground">
        <Link href="/billing" className="hover:text-foreground">
          Gérer l'abonnement principal →
        </Link>
      </div>
    </div>
  );
}

function BillingSkeleton() {
  return (
    <div className="space-y-6 max-w-4xl">
      <Skeleton className="h-8 w-64" />
      <div className="rounded-lg border bg-card p-6 space-y-4">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-10 w-80" />
        <Skeleton className="h-3 w-full" />
      </div>
      <div className="rounded-lg border bg-card p-6 space-y-3">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-20 w-full" />
      </div>
    </div>
  );
}
