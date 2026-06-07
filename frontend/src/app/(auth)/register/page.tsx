'use client';
import { LogoMark } from '@/components/brand/logo';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { CantonPicker } from '@/components/swiss/CantonPicker';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { validateCheVat } from '@/lib/ch';
import { api } from '@/lib/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

type PlanId = 'solo' | 'bureau' | 'enterprise';
const PLANS: { id: PlanId; name: string; monthly: number; yearly: number; livrables: string }[] = [
  { id: 'solo', name: 'Solo', monthly: 690, yearly: 6900, livrables: '~200 livrables / mois' },
  { id: 'bureau', name: 'Bureau', monthly: 2400, yearly: 24000, livrables: '~500 livrables / mois' },
  { id: 'enterprise', name: 'Enterprise', monthly: 4900, yearly: 49000, livrables: 'Volume sur mesure' },
];

export default function RegisterPage() {
  const router = useRouter();
  const [plan, setPlan] = useState<PlanId>('bureau');
  const [billingInterval, setBillingInterval] = useState<'monthly' | 'yearly'>('monthly');
  const [form, setForm] = useState({
    email: '',
    password: '',
    full_name: '',
    organization_name: '',
    country: 'CH',
    canton: 'GE',
    language: 'fr',
    currency: 'CHF',
    vat_number: '',
    address: '',
    postal_code: '',
    city: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pré-sélection du plan / intervalle depuis l'URL (deep-link depuis la landing).
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const p = (params.get('plan') || '').toLowerCase();
    if (p === 'solo' || p === 'bureau' || p === 'enterprise') setPlan(p);
    const i = (params.get('interval') || '').toLowerCase();
    if (i === 'monthly' || i === 'yearly') setBillingInterval(i);
  }, []);

  const handleChangeCountry = (country: string) => {
    setForm({
      ...form,
      country,
      currency: country === 'CH' ? 'CHF' : 'EUR',
      canton: country === 'CH' ? (form.canton || 'GE') : '',
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (form.country === 'CH' && form.vat_number && !validateCheVat(form.vat_number)) {
      setError('Format TVA incorrect. Attendu : CHE-123.456.789 (optionnellement suivi de MWST ou TVA)');
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }

      const { createClient } = await import('@/lib/supabase');
      const supabase = createClient();
      const { error: loginErr } = await supabase.auth.signInWithPassword({
        email: form.email,
        password: form.password,
      });
      if (loginErr) throw loginErr;

      // Paiement à la fin de la création : on envoie l'utilisateur vers Stripe
      // pour le plan choisi. Si Stripe est indisponible, on entre quand même
      // dans l'app (le forfait pourra être réglé depuis Facturation).
      try {
        const { checkout_url } = await api.checkout(plan, billingInterval);
        window.location.href = checkout_url;
        return;
      } catch {
        router.push('/dashboard');
        router.refresh();
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const selected = PLANS.find((p) => p.id === plan)!;
  const price = billingInterval === 'yearly' ? selected.yearly : selected.monthly;
  const cur = form.currency === 'CHF' ? 'CHF' : '€';

  return (
    <div className="min-h-screen grid place-items-center bg-muted/30 px-4 py-8">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <div className="flex items-center gap-2 mb-2">
            <LogoMark className="h-8 w-8" />
            <span className="font-semibold">LESO</span>
          </div>
          <CardTitle>Créer un compte</CardTitle>
          <CardDescription>
            Choisissez votre forfait, créez le compte, puis réglez en ligne. Essai 1 mois · résiliable à tout moment.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Sélecteur de plan + intervalle */}
          <div className="mb-6 space-y-3">
            <div className="flex items-center justify-between">
              <Label>Forfait</Label>
              <div className="inline-flex items-center rounded-lg border p-0.5 text-xs">
                <button
                  type="button"
                  onClick={() => setBillingInterval('monthly')}
                  className={`px-2.5 py-1 rounded-md transition-colors ${billingInterval === 'monthly' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  Mensuel
                </button>
                <button
                  type="button"
                  onClick={() => setBillingInterval('yearly')}
                  className={`px-2.5 py-1 rounded-md transition-colors ${billingInterval === 'yearly' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  Annuel <span className="text-emerald-600 font-medium">−17%</span>
                </button>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {PLANS.map((p) => {
                const active = p.id === plan;
                const pr = billingInterval === 'yearly' ? p.yearly : p.monthly;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setPlan(p.id)}
                    className={`rounded-lg border p-3 text-left transition-all ${active ? 'border-primary ring-1 ring-primary bg-primary/5' : 'hover:border-foreground/30'}`}
                  >
                    <div className="text-sm font-semibold">{p.name}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {pr.toLocaleString('fr-CH')} {cur}/{billingInterval === 'yearly' ? 'an' : 'mois'}
                    </div>
                    <div className="text-[11px] text-muted-foreground mt-1">{p.livrables}</div>
                  </button>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground">
              Sélection : <span className="font-medium text-foreground">{selected.name}</span> ·{' '}
              {price.toLocaleString('fr-CH')} {cur}/{billingInterval === 'yearly' ? 'an' : 'mois'} · Prix nets (TVA non applicable)
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Pays</Label>
                <Select value={form.country} onValueChange={handleChangeCountry}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CH">🇨🇭 Suisse</SelectItem>
                    <SelectItem value="FR">🇫🇷 France</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {form.country === 'CH' && (
                <div className="space-y-2">
                  <Label>Canton principal</Label>
                  <CantonPicker value={form.canton} onChange={(c) => setForm({ ...form, canton: c })} />
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="organization_name">Nom du bureau d'études *</Label>
              <Input id="organization_name" value={form.organization_name}
                onChange={(e) => setForm({ ...form, organization_name: e.target.value })} required />
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="full_name">Nom complet *</Label>
                <Input id="full_name" value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email professionnel *</Label>
                <Input id="email" type="email" value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })} required />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Mot de passe *</Label>
              <Input id="password" type="password" value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} />
              <p className="text-xs text-muted-foreground">8 caractères minimum</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="vat_number">
                {form.country === 'CH' ? 'Numéro TVA (CHE-XXX.XXX.XXX)' : 'Numéro TVA intracommunautaire'}
              </Label>
              <Input id="vat_number"
                placeholder={form.country === 'CH' ? 'CHE-123.456.789 MWST' : 'FR12345678901'}
                value={form.vat_number}
                onChange={(e) => setForm({ ...form, vat_number: e.target.value })} />
            </div>

            <div className="grid md:grid-cols-[2fr_1fr_2fr] gap-4">
              <div className="space-y-2">
                <Label htmlFor="address">Adresse</Label>
                <Input id="address" value={form.address}
                  onChange={(e) => setForm({ ...form, address: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="postal_code">NPA</Label>
                <Input id="postal_code" value={form.postal_code}
                  onChange={(e) => setForm({ ...form, postal_code: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="city">Ville</Label>
                <Input id="city" value={form.city}
                  onChange={(e) => setForm({ ...form, city: e.target.value })} />
              </div>
            </div>

            {error && <div className="text-sm text-destructive">{error}</div>}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Création…' : `Créer mon compte et régler (${price.toLocaleString('fr-CH')} ${cur}/${billingInterval === 'yearly' ? 'an' : 'mois'})`}
            </Button>
            <p className="text-[11px] text-muted-foreground text-center">
              Vous serez redirigé vers le paiement sécurisé Stripe après la création.
            </p>
          </form>

          <p className="text-sm text-muted-foreground text-center mt-4">
            Déjà inscrit ?{' '}
            <Link href="/login" className="text-foreground font-medium underline-offset-4 hover:underline">
              Se connecter
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
