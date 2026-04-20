import Link from 'next/link';
import { redirect } from 'next/navigation';
import {
  Flame, Building, Layers, Building2, Shield, Bell, ArrowRight, Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { createServerSupabase } from '@/lib/supabase';

export default async function LandingPage() {
  const supabase = await createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  if (user) redirect('/dashboard');

  const modules = [
    { icon: Flame, title: 'Thermique SIA 380/1', desc: 'Justificatifs avec export gbXML et import Lesosai' },
    { icon: Building, title: 'Structure SIA 260-267', desc: 'SAF pour Scia/RFEM + double-check M=qL²/8' },
    { icon: Layers, title: 'Pré-BIM', desc: 'Programme architectural → IFC 4 avec Psets thermiques' },
    { icon: Building2, title: 'IDC Genève', desc: 'Extraction factures + calcul OCEN + formulaire PDF' },
    { icon: Shield, title: 'AEAI incendie', desc: 'Checklists par typologie + rapport PDF' },
    { icon: Bell, title: 'Veille CH romande', desc: 'Fedlex + 6 cantons surveillés quotidiennement' },
  ];

  const plans = [
    {
      name: 'Starter', price: '690', tasks: '500',
      features: ['Tous modules CH', '1 utilisateur', 'Support email', '10 Go stockage'],
    },
    {
      name: 'Pro', price: '1 900', tasks: '2 000',
      features: ['+ Veille quotidienne', 'Multi-utilisateurs', '50 Go stockage', 'Support prioritaire'],
      highlight: true,
    },
    {
      name: 'Enterprise', price: '5 000', tasks: 'illimité',
      features: ['+ SLA 99.9%', 'Account manager', 'Intégrations sur mesure'],
    },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground">
      <nav className="border-b bg-background/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <div className="h-7 w-7 rounded-md bg-primary text-primary-foreground grid place-items-center text-sm font-bold">B</div>
            <span>BET Agent</span>
          </Link>
          <div className="flex items-center gap-2">
            <Link href="/login"><Button variant="ghost" size="sm">Se connecter</Button></Link>
            <Link href="/register"><Button size="sm">Essayer</Button></Link>
          </div>
        </div>
      </nav>

      <section className="max-w-5xl mx-auto px-6 py-20 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border bg-muted/40 text-xs text-muted-foreground mb-6">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Pour les bureaux d'études techniques de Suisse romande
        </div>
        <h1 className="text-4xl md:text-5xl font-semibold tracking-tight leading-[1.1] mb-5">
          L'agent IA pour justificatifs,<br />notes de calcul et déclarations.
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
          SIA 380/1, SIA 260-267, IDC Genève, AEAI, pré-BIM, veille réglementaire.
          Tout ce qui ralentit vos ingénieurs, automatisé — avec respect des licences SIA/AEAI et responsabilité humaine préservée.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link href="/register">
            <Button size="lg" className="gap-2">
              Créer un compte <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/login"><Button size="lg" variant="outline">Se connecter</Button></Link>
        </div>
        <p className="text-xs text-muted-foreground mt-5">
          Essai sans CB · Données hébergées en Suisse/UE · Conforme RGPD
        </p>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-16 border-t">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-semibold mb-2">Six modules métier</h2>
          <p className="text-sm text-muted-foreground">
            Chaque module automatise un livrable récurrent des BET de Suisse romande.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-3">
          {modules.map((m) => (
            <Card key={m.title} className="hover:shadow-sm transition-shadow">
              <CardContent className="pt-5 pb-5">
                <m.icon className="h-5 w-5 text-primary mb-3" />
                <h3 className="font-medium mb-1">{m.title}</h3>
                <p className="text-sm text-muted-foreground">{m.desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16 border-t">
        <div className="text-center">
          <h2 className="text-2xl font-semibold mb-4">L'humain garde la main</h2>
          <p className="text-muted-foreground mb-8">
            Les calculs officiels restent dans Lesosai, Scia, Robot ou les logiciels que vous utilisez déjà.
            L'agent produit un brouillon à 80%. L'ingénieur-architecte vérifie, complète, signe.
          </p>
          <div className="grid md:grid-cols-2 gap-4 text-left">
            {[
              'La responsabilité professionnelle reste à l\'humain qualifié',
              'Les normes SIA et AEAI ne sont jamais reproduites textuellement',
              'Double-check analytique M=qL²/8 sur chaque élément structure',
              'Veille Fedlex + 6 cantons romands, alerte email par projet impacté',
            ].map((txt) => (
              <div key={txt} className="flex items-start gap-2">
                <Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />
                <p className="text-sm">{txt}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-16 border-t">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-semibold mb-2">Tarification transparente</h2>
          <p className="text-sm text-muted-foreground">En CHF · mensuel · TVA 8.1%</p>
        </div>
        <div className="grid md:grid-cols-3 gap-4">
          {plans.map((plan) => (
            <Card key={plan.name} className={plan.highlight ? 'border-primary shadow-md' : ''}>
              <CardContent className="pt-6 pb-6">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{plan.name}</h3>
                  {plan.highlight && (
                    <span className="text-xs bg-primary text-primary-foreground px-2 py-0.5 rounded">Populaire</span>
                  )}
                </div>
                <div className="mb-1">
                  <span className="text-3xl font-bold">{plan.price}</span>
                  <span className="text-sm text-muted-foreground"> CHF/mois</span>
                </div>
                <p className="text-xs text-muted-foreground mb-5">{plan.tasks} tâches par mois</p>
                <ul className="space-y-2 mb-5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <Check className="h-3.5 w-3.5 text-emerald-600 mt-0.5 shrink-0" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <Link href="/register" className="block">
                  <Button variant={plan.highlight ? 'default' : 'outline'} className="w-full">
                    Commencer
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <footer className="border-t mt-8">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 rounded bg-primary text-primary-foreground grid place-items-center text-xs font-bold">B</div>
            <span>BET Agent · Lausanne</span>
          </div>
          <div className="flex items-center gap-6 text-xs">
            <Link href="/login" className="hover:text-foreground">Connexion</Link>
            <Link href="/register" className="hover:text-foreground">Créer un compte</Link>
            <a href="mailto:team@bet-agent.ch" className="hover:text-foreground">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
