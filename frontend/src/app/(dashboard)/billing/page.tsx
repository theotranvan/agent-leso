'use client';
import { useEffect, useState } from 'react';
import { Check, ExternalLink, Lock } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';

const PLANS = [
  {
    id: 'solo',
    name: 'Solo',
    price: 690,
    priceYearly: 6900,
    livrables: '~200 livrables / mois',
    features: ['CCTP, notes de calcul, chiffrages', 'Coordination IFC', '1 utilisateur', 'Support email'],
  },
  {
    id: 'bureau',
    name: 'Bureau',
    price: 2400,
    priceYearly: 24000,
    livrables: '~500 livrables / mois',
    features: ['Tout Solo', 'Veille réglementaire quotidienne', 'Utilisateurs illimités', 'Validation déléguée', 'Support prioritaire'],
    highlight: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 'dès 4 900',
    priceYearly: 'dès 49 000',
    livrables: 'Volume sur mesure',
    features: ['Tout Bureau', 'SLA 99.9%', 'Account manager dédié', 'Intégrations sur mesure'],
  },
];

export default function BillingPage() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [billingInterval, setBillingInterval] = useState<'monthly' | 'yearly'>('monthly');

  useEffect(() => {
    api.getBillingStatus().then(setStatus).finally(() => setLoading(false));
  }, []);

  const handleUpgrade = async (plan: 'solo' | 'bureau' | 'enterprise') => {
    setUpgrading(plan);
    try {
      const { checkout_url } = await api.checkout(plan, billingInterval);
      window.location.href = checkout_url;
    } catch (e: any) {
      alert(`Erreur : ${e.message}`);
      setUpgrading(null);
    }
  };

  const handlePortal = async () => {
    try {
      const { portal_url } = await api.billingPortal();
      window.location.href = portal_url;
    } catch (e: any) {
      alert(`Erreur : ${e.message}`);
    }
  };

  if (loading) return <div className="text-muted-foreground">Chargement...</div>;

  const quotaPct = status ? Math.round(status.quota_pct ?? 0) : 0;
  const fmtTokens = (n?: number) =>
    n == null ? '—' : n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1000 ? `${Math.round(n / 1000)}k` : `${n}`;
  const betaMode = status?.beta_mode !== false; // par défaut bêta tant que non démenti
  const contact = status?.billing_contact || 'theo.cours34@gmail.com';

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Facturation</h1>
        <p className="text-sm text-muted-foreground mt-1">Gérez votre abonnement et consultez votre consommation</p>
      </div>

      {betaMode && (
        <Card className="border-amber-300 bg-amber-50/60">
          <CardContent className="flex items-start gap-3 py-4 text-sm">
            <Lock className="h-4 w-4 mt-0.5 shrink-0 text-amber-700" />
            <div>
              <p className="font-medium text-amber-900">Paiement en ligne en cours de déploiement</p>
              <p className="text-amber-800 mt-0.5">
                Pendant la bêta, le règlement et le changement de forfait se font directement avec nous —
                écrivez à{' '}
                <a href={`mailto:${contact}?subject=Forfait%20LESO`} className="font-medium underline">
                  {contact}
                </a>
                . Les boutons de paiement seront activés à la sortie de bêta.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Consommation du mois</CardTitle>
          <CardDescription>
            Plan <span className="font-medium text-foreground capitalize">{status?.plan}</span> ·{' '}
            {status?.livrables_used ?? 0} / {status?.livrables_limit ?? 0} livrables
            <span className="text-muted-foreground"> ({fmtTokens(status?.tokens_used)} / {fmtTokens(status?.tokens_limit)} tokens)</span>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Progress value={quotaPct} />
          <div className="flex justify-between items-center">
            <p className="text-xs text-muted-foreground">{quotaPct}% du quota consommé</p>
            {!betaMode && status?.stripe_subscription_id && (
              <Button variant="outline" size="sm" onClick={handlePortal}>
                <ExternalLink className="h-4 w-4 mr-2" />
                Gérer l'abonnement (Stripe)
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <div>
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h2 className="text-lg font-semibold">Plans disponibles</h2>
          <div className="inline-flex items-center rounded-lg border p-0.5 text-sm">
            <button
              onClick={() => setBillingInterval('monthly')}
              className={`px-3 py-1 rounded-md transition-colors ${billingInterval === 'monthly' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            >
              Mensuel
            </button>
            <button
              onClick={() => setBillingInterval('yearly')}
              className={`px-3 py-1 rounded-md transition-colors ${billingInterval === 'yearly' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            >
              Annuel <span className="text-emerald-600 font-medium">−17 %</span>
            </button>
          </div>
        </div>
        <p className="text-xs text-muted-foreground mb-4">Prix nets · TVA non applicable</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PLANS.map((plan) => {
            const isCurrent = status?.plan === plan.id;
            const shownPrice = billingInterval === 'yearly' ? plan.priceYearly : plan.price;
            return (
              <Card key={plan.id} className={plan.highlight ? 'border-primary' : ''}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>{plan.name}</CardTitle>
                    {plan.highlight && <Badge>Populaire</Badge>}
                  </div>
                  <div className="mt-2">
                    <span className="text-3xl font-bold">{shownPrice}</span>
                    <span className="text-sm text-muted-foreground">
                      {' '}{status?.currency || 'CHF'} / {billingInterval === 'yearly' ? 'an' : 'mois'}
                    </span>
                  </div>
                  {billingInterval === 'yearly' && (
                    <p className="text-xs text-emerald-600 mt-0.5">2 mois offerts</p>
                  )}
                  <CardDescription>{plan.livrables}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-2">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-start gap-2 text-sm">
                        <Check className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                  {betaMode ? (
                    <Button className="w-full" variant="outline" disabled>
                      <Lock className="h-4 w-4 mr-2" />
                      {isCurrent ? 'Plan actuel' : 'Bientôt disponible'}
                    </Button>
                  ) : (
                    <Button
                      className="w-full"
                      variant={isCurrent ? 'outline' : plan.highlight ? 'default' : 'outline'}
                      disabled={isCurrent || upgrading !== null}
                      onClick={() => handleUpgrade(plan.id as any)}
                    >
                      {isCurrent
                        ? 'Plan actuel'
                        : upgrading === plan.id
                          ? 'Redirection...'
                          : status?.stripe_subscription_id
                            ? 'Changer pour ce plan'
                            : 'Choisir ce plan'}
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
