'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Building2, Palette, FolderPlus, Check, ChevronRight, ArrowRight, SkipForward,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Banner } from '@/components/ui/banner';

const CANTONS = ['VD', 'GE', 'FR', 'VS', 'NE', 'JU'];
const LABELS = ['Minergie', 'Minergie-P', 'Minergie-A', 'CVSE', 'CECB', 'SméO'];
const PHASES = [
  { key: 'avant_projet', label: 'Avant-projet (SIA 31)' },
  { key: 'projet_ouvrage', label: 'Projet de l\'ouvrage (SIA 32)' },
  { key: 'autorisation', label: 'Autorisation (SIA 33)' },
  { key: 'appel_offres', label: 'Appel d\'offres (SIA 41)' },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Étape 1 — organisation
  const [orgName, setOrgName] = useState('');
  const [canton, setCanton] = useState('VD');
  const [teamSize, setTeamSize] = useState('');

  // Étape 2 — branding
  const [primaryColor, setPrimaryColor] = useState('#1B3A5C');
  const [accentColor, setAccentColor] = useState('#2E75B6');
  const [footerText, setFooterText] = useState('');

  // Étape 3 — premier projet
  const [projName, setProjName] = useState('');
  const [projAddress, setProjAddress] = useState('');
  const [projCommune, setProjCommune] = useState('');
  const [projSre, setProjSre] = useState('');
  const [projLabels, setProjLabels] = useState<string[]>([]);
  const [projPhase, setProjPhase] = useState('avant_projet');

  useEffect(() => {
    api.onboarding.getState().then((s) => {
      if (s.completed) router.replace('/dashboard');
      else setStep(s.step || 0);
    }).catch(() => {});
  }, [router]);

  const steps = [
    { icon: Building2, label: 'Votre bureau' },
    { icon: Palette, label: 'Charte graphique' },
    { icon: FolderPlus, label: 'Première affaire' },
  ];

  const submitOrg = async () => {
    setSaving(true); setError(null);
    try {
      await api.onboarding.stepOrganization({ name: orgName, canton, team_size: teamSize });
      setStep(1);
    } catch (e: any) { setError(e?.message || 'Erreur'); }
    finally { setSaving(false); }
  };

  const submitBranding = async () => {
    setSaving(true); setError(null);
    try {
      await api.onboarding.stepBranding({
        primary_color: primaryColor, accent_color: accentColor,
        full_name: orgName, footer_text: footerText,
      });
      setStep(2);
    } catch (e: any) { setError(e?.message || 'Erreur'); }
    finally { setSaving(false); }
  };

  const submitProject = async () => {
    setSaving(true); setError(null);
    try {
      const r = await api.onboarding.stepFirstProject({
        name: projName || 'Ma première affaire',
        address: projAddress, commune: projCommune, canton,
        sre_m2: projSre ? Number(projSre) : undefined,
        labels: projLabels, phase_sia_demarrage: projPhase,
      });
      router.replace(r.project_id ? `/projects/${r.project_id}` : '/dashboard');
    } catch (e: any) { setError(e?.message || 'Erreur'); }
    finally { setSaving(false); }
  };

  const skip = async () => {
    await api.onboarding.skip().catch(() => {});
    router.replace('/dashboard');
  };

  return (
    <div className="mx-auto max-w-2xl py-8">
      {/* Stepper */}
      <div className="mb-8 flex items-center justify-center gap-2">
        {steps.map((s, i) => (
          <div key={i} className="flex items-center">
            <div
              className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-medium ${
                i < step ? 'bg-green-600 text-white'
                : i === step ? 'bg-primary text-primary-foreground'
                : 'bg-secondary text-muted-foreground'
              }`}
            >
              {i < step ? <Check className="h-4 w-4" /> : i + 1}
            </div>
            {i < steps.length - 1 && (
              <div className={`mx-1 h-0.5 w-12 ${i < step ? 'bg-green-600' : 'bg-border'}`} />
            )}
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-border/60 bg-background p-8">
        {error && <Banner variant="error" className="mb-4">{error}</Banner>}

        {step === 0 && (
          <div className="space-y-5">
            <div>
              <h1 className="text-xl font-semibold">Bienvenue dans LESO</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Configurons votre bureau en quelques étapes pour démarrer.
              </p>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Nom du bureau</label>
              <input
                value={orgName} onChange={(e) => setOrgName(e.target.value)}
                placeholder="Conti Engineering SA"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Canton principal</label>
              <div className="flex flex-wrap gap-2">
                {CANTONS.map((c) => (
                  <button key={c} onClick={() => setCanton(c)}
                    className={`rounded-lg border px-4 py-2 text-sm ${
                      canton === c ? 'border-primary bg-primary/10 font-medium' : 'border-border'
                    }`}>{c}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Taille de l'équipe</label>
              <select value={teamSize} onChange={(e) => setTeamSize(e.target.value)}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm">
                <option value="">Sélectionner…</option>
                <option value="1">Indépendant</option>
                <option value="2-5">2 à 5 personnes</option>
                <option value="6-20">6 à 20 personnes</option>
                <option value="20+">Plus de 20 personnes</option>
              </select>
            </div>
            <div className="flex items-center justify-between pt-2">
              <button onClick={skip} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
                <SkipForward className="h-3.5 w-3.5" /> Passer
              </button>
              <Button onClick={submitOrg} disabled={!orgName || saving}>
                Continuer <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-5">
            <div>
              <h1 className="text-xl font-semibold">Votre charte graphique</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Vos documents (CCTP, rapports, PDF) sortiront à vos couleurs.
              </p>
            </div>
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="mb-1.5 block text-sm font-medium">Couleur principale</label>
                <div className="flex items-center gap-2">
                  <input type="color" value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)}
                    className="h-10 w-14 rounded border border-border" />
                  <input value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)}
                    className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="flex-1">
                <label className="mb-1.5 block text-sm font-medium">Couleur accent</label>
                <div className="flex items-center gap-2">
                  <input type="color" value={accentColor} onChange={(e) => setAccentColor(e.target.value)}
                    className="h-10 w-14 rounded border border-border" />
                  <input value={accentColor} onChange={(e) => setAccentColor(e.target.value)}
                    className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm" />
                </div>
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Pied de page des documents</label>
              <input value={footerText} onChange={(e) => setFooterText(e.target.value)}
                placeholder="Conti Engineering SA — av. de Rumine 13 — 1005 Lausanne"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm" />
            </div>
            {/* Aperçu */}
            <div className="rounded-lg border border-border p-4" style={{ borderTopWidth: 4, borderTopColor: primaryColor }}>
              <div className="text-sm font-semibold" style={{ color: primaryColor }}>{orgName || 'Votre bureau'}</div>
              <div className="mt-1 h-2 w-24 rounded" style={{ background: accentColor }} />
              <p className="mt-2 text-xs text-muted-foreground">{footerText || 'Aperçu de votre charte sur les documents'}</p>
            </div>
            <div className="flex items-center justify-between pt-2">
              <button onClick={() => setStep(0)} className="text-sm text-muted-foreground hover:text-foreground">Retour</button>
              <Button onClick={submitBranding} disabled={saving}>
                Continuer <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <div>
              <h1 className="text-xl font-semibold">Votre première affaire</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Créons un projet pour que vous puissiez démarrer immédiatement.
              </p>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Nom de l'affaire</label>
              <input value={projName} onChange={(e) => setProjName(e.target.value)}
                placeholder="Résidence Les Cerisiers"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm" />
            </div>
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="mb-1.5 block text-sm font-medium">Commune</label>
                <input value={projCommune} onChange={(e) => setProjCommune(e.target.value)}
                  placeholder="Lausanne"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm" />
              </div>
              <div className="w-32">
                <label className="mb-1.5 block text-sm font-medium">SRE (m²)</label>
                <input value={projSre} onChange={(e) => setProjSre(e.target.value)} type="number"
                  placeholder="3200"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm" />
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Labels visés</label>
              <div className="flex flex-wrap gap-2">
                {LABELS.map((l) => (
                  <button key={l}
                    onClick={() => setProjLabels((prev) => prev.includes(l) ? prev.filter((x) => x !== l) : [...prev, l])}
                    className={`rounded-lg border px-3 py-1.5 text-sm ${
                      projLabels.includes(l) ? 'border-primary bg-primary/10 font-medium' : 'border-border'
                    }`}>{l}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Phase de démarrage</label>
              <select value={projPhase} onChange={(e) => setProjPhase(e.target.value)}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm">
                {PHASES.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
              </select>
            </div>
            <div className="flex items-center justify-between pt-2">
              <button onClick={() => setStep(1)} className="text-sm text-muted-foreground hover:text-foreground">Retour</button>
              <Button onClick={submitProject} disabled={saving}>
                Terminer <Check className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
