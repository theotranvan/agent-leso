'use client';
import { useEffect, useState } from 'react';
import { Check, ExternalLink } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';

const PLANS = [
  {
    id: 'starter',
    name: 'Starter',
    price: 690,
    tasks: 500,
    features: ['CCTP, notes de calcul, chiffrages', 'Coordination IFC', 'Support email', 'Stockage documents 10 Go'],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 1900,
    tasks: 2000,
    features: ['Tout Starter', 'Veille réglementaire quotidienne', 'Multi-utilisateurs illimité', 'Stockage 50 Go', 'Support prioritaire'],
    highlight: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 5000,
    tasks: 'Illimité',
    features: ['Tout Pro', 'Tâches illimitées', 'SLA 99.9%', 'Account manager dédié', 'Intégrations sur mesure'],
  },
];

export default function BillingPage() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);

  useEffect(() => {
    api.getBillingStatus().then(setStatus).finally(() => setLoading(false));
  }, []);

  const handleUpgrade = async (plan: 'starter' | 'pro' | 'enterprise') => {
    setUpgrading(plan);
    try {
      const { checkout_url } = await api.checkout(plan);
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

  const quotaPct = status ? Math.round((status.tasks_used_this_month / Math.max(status.tasks_limit, 1)) * 100) : 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Facturation</h1>
        <p className="text-sm text-muted-foreground mt-1">Gérez votre abonnement et consultez votre consommation</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Consommation du mois</CardTitle>
          <CardDescription>
            Plan <span className="font-medium text-foreground capitalize">{status?.plan}</span> · {status?.tasks_used_this_month} / {status?.tasks_limit} tâches
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Progress value={quotaPct} />
          <div className="flex justify-between items-center">
            <p className="text-xs text-muted-foreground">{quotaPct}% du quota consommé</p>
            {status?.stripe_subscription_id && (
              <Button variant="outline" size="sm" onClick={handlePortal}>
                <ExternalLink className="h-4 w-4 mr-2" />
                Gérer l'abonnement (Stripe)
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <div>
        <h2 className="text-lg font-semibold mb-4">Plans disponibles</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PLANS.map((plan) => {
            const isCurrent = status?.plan === plan.id;
            return (
              <Card key={plan.id} className={plan.highlight ? 'border-primary' : ''}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>{plan.name}</CardTitle>
                    {plan.highlight && <Badge>Populaire</Badge>}
                  </div>
                  <div className="mt-2">
                    <span className="text-3xl font-bold">{plan.price}</span>
                    <span className="text-sm text-muted-foreground">
                      {' '}{status?.currency || 'CHF'} / mois HT
                    </span>
                  </div>
                  <CardDescription>
                    {typeof plan.tasks === 'number' ? `${plan.tasks.toLocaleString('fr-CH')} tâches / mois` : plan.tasks}
                  </CardDescription>
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
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
