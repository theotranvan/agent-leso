'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Palette, Loader2, Check, Building2 } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Banner } from '@/components/ui/banner';
import { Skeleton } from '@/components/ui/skeleton';

export default function ChartePage() {
  const [config, setConfig] = useState<any>({
    full_name: '', address: '', phone: '', email: '', website: '',
    logo_url: '', primary_color: '#1B2E4E', accent_color: '#2E75B6',
    signature_block: '', footer_text: '', confidentiality: 'Confidentiel',
  });
  const [orgName, setOrgName] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.settings.getBranding()
      .then((r) => {
        setOrgName(r.organization_name || '');
        if (r.branding_config) setConfig((c: any) => ({ ...c, ...r.branding_config }));
      })
      .catch((e: any) => setError(e?.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await api.settings.updateBranding(config);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: any) {
      setError(e?.message || 'Erreur');
    } finally {
      setSaving(false);
    }
  };

  const set = (k: string, v: any) => setConfig((c: any) => ({ ...c, [k]: v }));

  if (loading) {
    return (
      <div className="space-y-4 max-w-2xl">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <Link href="/settings" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1 mb-3">
          <ArrowLeft className="h-3.5 w-3.5" /> Paramètres
        </Link>
        <div className="flex items-center gap-2.5 mb-1">
          <Palette className="h-5 w-5 text-primary" />
          <h1 className="text-2xl font-semibold">Charte graphique</h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Personnalise l'apparence de tous tes documents générés (CCTP, rapports, dossiers).
          Ces réglages s'appliquent automatiquement à chaque PDF.
        </p>
      </div>

      {error && <Banner variant="error" onDismiss={() => setError(null)}>{error}</Banner>}
      {saved && <Banner variant="success">Charte enregistrée. Les prochains documents l'utiliseront.</Banner>}

      {/* Identité */}
      <section className="rounded-lg border bg-card p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-muted-foreground" />
          <h2 className="font-medium">Identité du bureau</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <Label>Raison sociale complète</Label>
            <Input value={config.full_name || ''} placeholder={orgName}
              onChange={(e) => set('full_name', e.target.value)} />
          </div>
          <div className="sm:col-span-2">
            <Label>Adresse</Label>
            <Input value={config.address || ''}
              onChange={(e) => set('address', e.target.value)} />
          </div>
          <div>
            <Label>Téléphone</Label>
            <Input value={config.phone || ''}
              onChange={(e) => set('phone', e.target.value)} />
          </div>
          <div>
            <Label>Email</Label>
            <Input value={config.email || ''}
              onChange={(e) => set('email', e.target.value)} />
          </div>
          <div className="sm:col-span-2">
            <Label>Site web</Label>
            <Input value={config.website || ''}
              onChange={(e) => set('website', e.target.value)} />
          </div>
        </div>
      </section>

      {/* Logo + couleurs */}
      <section className="rounded-lg border bg-card p-5 space-y-4">
        <h2 className="font-medium">Identité visuelle</h2>
        <div>
          <Label>URL du logo</Label>
          <Input value={config.logo_url || ''} placeholder="https://..."
            onChange={(e) => set('logo_url', e.target.value)} />
          <p className="text-xs text-muted-foreground mt-1">
            Téléverse ton logo dans Documents puis colle son URL ici.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Couleur principale</Label>
            <div className="flex items-center gap-2 mt-1">
              <input type="color" value={config.primary_color || '#1B2E4E'}
                onChange={(e) => set('primary_color', e.target.value)}
                className="h-9 w-12 rounded border cursor-pointer" />
              <Input value={config.primary_color || ''}
                onChange={(e) => set('primary_color', e.target.value)} className="flex-1" />
            </div>
          </div>
          <div>
            <Label>Couleur d'accent</Label>
            <div className="flex items-center gap-2 mt-1">
              <input type="color" value={config.accent_color || '#2E75B6'}
                onChange={(e) => set('accent_color', e.target.value)}
                className="h-9 w-12 rounded border cursor-pointer" />
              <Input value={config.accent_color || ''}
                onChange={(e) => set('accent_color', e.target.value)} className="flex-1" />
            </div>
          </div>
        </div>
        {/* Aperçu */}
        <div className="rounded-md border overflow-hidden">
          <div className="px-4 py-3 flex items-center justify-between"
            style={{ borderBottom: `2px solid ${config.accent_color}` }}>
            <span className="font-semibold text-sm" style={{ color: config.primary_color }}>
              {config.full_name || orgName || 'Votre bureau'}
            </span>
            <span className="text-xs text-muted-foreground">Aperçu en-tête document</span>
          </div>
          <div className="px-4 py-3">
            <div className="text-base font-semibold mb-1" style={{ color: config.primary_color }}>
              CCTP — Lot Chauffage
            </div>
            <div className="h-0.5 w-16 mb-2" style={{ background: config.accent_color }} />
            <p className="text-xs text-muted-foreground">
              Aperçu du rendu de vos documents avec cette charte.
            </p>
          </div>
        </div>
      </section>

      {/* Signature + pied de page */}
      <section className="rounded-lg border bg-card p-5 space-y-4">
        <h2 className="font-medium">Signature et mentions</h2>
        <div>
          <Label>Bloc signature</Label>
          <Input value={config.signature_block || ''}
            placeholder="Ing. Jean Dupont, ingénieur CVS dipl. EPF"
            onChange={(e) => set('signature_block', e.target.value)} />
        </div>
        <div>
          <Label>Texte de pied de page</Label>
          <Input value={config.footer_text || ''}
            placeholder="Conti Ingénierie SA · Lausanne"
            onChange={(e) => set('footer_text', e.target.value)} />
        </div>
        <div>
          <Label>Mention de confidentialité</Label>
          <Input value={config.confidentiality || ''}
            onChange={(e) => set('confidentiality', e.target.value)} />
        </div>
      </section>

      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={saving} className="gap-2">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : saved ? <Check className="h-4 w-4" /> : null}
          {saving ? 'Enregistrement…' : saved ? 'Enregistré' : 'Enregistrer la charte'}
        </Button>
      </div>
    </div>
  );
}
