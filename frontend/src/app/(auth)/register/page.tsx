'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { CantonPicker } from '@/components/swiss/CantonPicker';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { validateCheVat } from '@/lib/ch';

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

export default function RegisterPage() {
  const router = useRouter();
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

      router.push('/dashboard');
      router.refresh();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const planPrice = form.currency === 'CHF' ? '690 CHF' : '690 €';

  return (
    <div className="min-h-screen grid place-items-center bg-muted/30 px-4 py-8">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <div className="flex items-center gap-2 mb-2">
            <div className="h-8 w-8 rounded-md bg-primary text-primary-foreground grid place-items-center font-bold">B</div>
            <span className="font-semibold">BET Agent</span>
          </div>
          <CardTitle>Créer un compte</CardTitle>
          <CardDescription>Plan Starter {planPrice} / mois · 500 tâches</CardDescription>
        </CardHeader>
        <CardContent>
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
              {loading ? 'Création...' : 'Créer mon compte'}
            </Button>
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
