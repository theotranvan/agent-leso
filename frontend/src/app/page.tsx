import Link from 'next/link';
import { redirect } from 'next/navigation';
import {
  Flame, Building, Building2, Shield, Bell, ArrowRight, Check,
  Sparkles, FileCheck2, ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Logo } from '@/components/brand/logo';
import { Reveal } from '@/components/brand/reveal';
import { createServerSupabase } from '@/lib/supabase-server';

export default async function LandingPage() {
  const supabase = await createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  if (user) redirect('/dashboard');

  const stats = [
    { v: '~1 jour', l: 'économisé par CCTP' },
    { v: '5 min', l: 'pour un justificatif' },
    { v: '31 normes', l: 'suisses couvertes' },
    { v: '100 %', l: 'à votre charte' },
  ];

  const steps = [
    { n: '01', title: 'Décrivez l’affaire', desc: 'Surfaces, labels visés — ou déposez votre maquette IFC, l’agent en extrait les données.' },
    { n: '02', title: 'L’agent rédige', desc: 'CCTP, note de calcul ou justificatif, produit en minutes, aux normes SIA en vigueur.' },
    { n: '03', title: 'Vous validez', desc: 'L’IA signale les points sensibles. Vous gardez le dernier mot et la signature.' },
  ];

  const modules = [
    { icon: Flame, title: 'Thermique SIA 380/1', desc: 'Justificatifs Minergie, export vers Lesosai, lecture IFC.' },
    { icon: Building, title: 'Structure SIA 260', desc: 'Notes de calcul, export Scia/RFEM, double-vérification.' },
    { icon: FileCheck2, title: 'CCTP & métrés', desc: 'Descriptifs et bordereaux par lot CFC, prix KBOB romands.' },
    { icon: Building2, title: 'IDC Genève', desc: 'Calcul OCEN, formulaires pré-remplis, lecture des factures.' },
    { icon: Shield, title: 'AEAI incendie', desc: 'Checklists par typologie, rapports prêts à déposer.' },
    { icon: Bell, title: 'Veille romande', desc: 'Fedlex et cantons surveillés, résumé mensuel ciblé.' },
  ];

  const plans = [
    {
      name: 'Starter', price: '690', tagline: 'Bureau indépendant', tasks: '500 documents / mois',
      features: ['Tous les modules suisses', '1 utilisateur', 'Documents à votre charte', 'Support par email'],
    },
    {
      name: 'Pro', price: '1 900', tagline: 'Bureau de 5 à 20 personnes', tasks: '2 000 documents / mois',
      features: ['Tout Starter, plus :', 'Utilisateurs illimités', 'Veille personnalisée', 'Validation déléguée', 'Vue multi-affaires', 'Support prioritaire'],
      highlight: true,
    },
    {
      name: 'Enterprise', price: '5 000', tagline: 'Grand bureau', tasks: 'Documents illimités',
      features: ['Tout Pro, plus :', 'SLA 99.9 %', 'Account manager dédié', 'Intégrations sur mesure'],
    },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Nav */}
      <nav className="border-b bg-background/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <Logo />
          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#fonctionnement" className="hover:text-foreground transition-colors">Comment ça marche</a>
            <a href="#modules" className="hover:text-foreground transition-colors">Modules</a>
            <a href="#tarifs" className="hover:text-foreground transition-colors">Tarifs</a>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login"><Button variant="ghost" size="sm">Se connecter</Button></Link>
            <Link href="/register"><Button size="sm">Créer mon compte</Button></Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-24 pb-20 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border bg-card text-xs text-muted-foreground mb-6 animate-in fade-in slide-in-from-bottom-2 duration-700">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Conçu pour les bureaux d’études techniques de Suisse romande
        </div>
        <h1 className="text-4xl md:text-6xl font-semibold tracking-tight leading-[1.05] mb-6 animate-in fade-in slide-in-from-bottom-3 duration-700">
          Vos dossiers techniques,<br />produits en minutes.<br />
          <span className="text-muted-foreground">Pas en jours.</span>
        </h1>
        <p className="text-lg md:text-xl text-muted-foreground max-w-xl mx-auto mb-9 animate-in fade-in slide-in-from-bottom-4 duration-700">
          CCTP, notes de calcul, justificatifs thermiques — rédigés aux normes
          suisses, à votre charte. Vous gardez le contrôle et la signature.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 animate-in fade-in slide-in-from-bottom-5 duration-700">
          <Link href="/register">
            <Button size="lg" className="gap-2 w-full sm:w-auto group">
              Créer mon compte
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Button>
          </Link>
          <a href="#fonctionnement">
            <Button size="lg" variant="outline" className="w-full sm:w-auto">Voir comment ça marche</Button>
          </a>
        </div>
        <p className="text-xs text-muted-foreground mt-5">
          Données hébergées en Suisse / UE · Vos documents restent les vôtres
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-16">
          {stats.map((s, i) => (
            <Reveal key={s.l} delay={i * 80}>
              <div className="rounded-xl border bg-card p-4 transition-shadow hover:shadow-sm">
                <div className="text-2xl font-semibold tracking-tight">{s.v}</div>
                <div className="text-xs text-muted-foreground mt-1">{s.l}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Comment ça marche */}
      <section id="fonctionnement" className="border-t bg-muted/10">
        <div className="max-w-5xl mx-auto px-6 py-20">
          <Reveal className="text-center max-w-xl mx-auto mb-14">
            <div className="inline-flex items-center gap-2 text-sm text-primary font-medium mb-3">
              <Sparkles className="h-4 w-4" /> Trois étapes
            </div>
            <h2 className="text-3xl font-semibold tracking-tight">
              Et le dossier est prêt.
            </h2>
          </Reveal>
          <div className="grid md:grid-cols-3 gap-6">
            {steps.map((s, i) => (
              <Reveal key={s.n} delay={i * 120}>
                <div className="relative rounded-2xl border bg-card p-6 h-full">
                  <div className="text-4xl font-semibold text-muted-foreground/25 mb-3">{s.n}</div>
                  <h3 className="font-semibold mb-2">{s.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
                  {i < steps.length - 1 && (
                    <ChevronRight className="hidden md:block absolute -right-4 top-1/2 -translate-y-1/2 h-6 w-6 text-muted-foreground/25" />
                  )}
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Modules */}
      <section id="modules" className="max-w-5xl mx-auto px-6 py-20">
        <Reveal className="text-center max-w-xl mx-auto mb-14">
          <h2 className="text-3xl font-semibold tracking-tight mb-3">Tout votre métier, couvert.</h2>
          <p className="text-muted-foreground">
            Du justificatif thermique au dossier incendie, chaque livrable d’un BET romand.
          </p>
        </Reveal>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {modules.map((m, i) => (
            <Reveal key={m.title} delay={(i % 3) * 80}>
              <div className="rounded-2xl border bg-card p-6 h-full transition-all hover:shadow-md hover:-translate-y-0.5">
                <div className="h-11 w-11 rounded-xl bg-primary/10 text-primary grid place-items-center mb-4">
                  <m.icon className="h-5 w-5" />
                </div>
                <h3 className="font-semibold mb-2">{m.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{m.desc}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Confiance / contrôle */}
      <section className="border-t bg-muted/10">
        <div className="max-w-5xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-12 items-center">
          <Reveal>
            <h2 className="text-3xl font-semibold tracking-tight mb-4">
              L’IA propose. Vous décidez.
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-6">
              Chaque document reçoit un score de confiance et ne vous remonte que les
              points à vérifier — vous ne relisez pas 40 pages pour en corriger deux.
            </p>
            <ul className="space-y-3">
              {[
                'Score de confiance sur chaque livrable',
                'Seuls les points sensibles sont signalés',
                'Validation en un clic, au bureau ou en mobilité',
                'Votre signature, votre responsabilité',
              ].map((f) => (
                <li key={f} className="flex items-start gap-3 text-sm">
                  <Check className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal delay={120}>
            <div className="rounded-2xl border bg-card p-8 shadow-sm">
              <div className="flex items-center gap-4 mb-6">
                <div className="h-14 w-14 rounded-full bg-emerald-50 text-emerald-600 grid place-items-center text-lg font-bold">94</div>
                <div>
                  <div className="font-semibold">CCTP Ventilation</div>
                  <div className="text-sm text-emerald-600 font-medium">Confiance élevée · prêt à approuver</div>
                </div>
              </div>
              <div className="space-y-1 text-sm">
                {[
                  ['Normes citées', 'SIA 382/1'],
                  ['Anomalies détectées', 'Aucune'],
                  ['Complétude', '100 %'],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between items-center py-2 border-b last:border-0">
                    <span className="text-muted-foreground">{k}</span>
                    <span className="font-medium">{v}</span>
                  </div>
                ))}
              </div>
              <Button className="w-full mt-6 gap-2 bg-emerald-600 hover:bg-emerald-700">
                <Check className="h-4 w-4" /> Approuver le document
              </Button>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Tarifs */}
      <section id="tarifs" className="max-w-5xl mx-auto px-6 py-20">
        <Reveal className="text-center max-w-xl mx-auto mb-14">
          <h2 className="text-3xl font-semibold tracking-tight mb-3">Un tarif simple, tout inclus.</h2>
          <p className="text-muted-foreground">
            Tous les modules dans chaque plan. Vous ne payez que le volume.
          </p>
        </Reveal>
        <div className="grid md:grid-cols-3 gap-6 items-start">
          {plans.map((plan, i) => (
            <Reveal key={plan.name} delay={i * 100}>
              <div
                className={`rounded-2xl border p-7 relative bg-card transition-shadow hover:shadow-md ${plan.highlight ? 'border-primary shadow-lg md:scale-105' : ''}`}
              >
                {plan.highlight && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-primary text-primary-foreground text-xs font-medium">
                    Le plus choisi
                  </div>
                )}
                <div className="mb-1 font-semibold text-lg">{plan.name}</div>
                <div className="text-sm text-muted-foreground mb-4">{plan.tagline}</div>
                <div className="flex items-baseline gap-1 mb-1">
                  <span className="text-4xl font-semibold tracking-tight">{plan.price}</span>
                  <span className="text-muted-foreground">CHF / mois</span>
                </div>
                <div className="text-sm text-muted-foreground mb-6">{plan.tasks}</div>
                <Link href="/register">
                  <Button className="w-full mb-6" variant={plan.highlight ? 'default' : 'outline'}>
                    Commencer
                  </Button>
                </Link>
                <ul className="space-y-3">
                  {plan.features.map((f) => (
                    <li key={f} className={`flex items-start gap-2.5 text-sm ${f.endsWith(':') ? 'font-medium text-foreground' : ''}`}>
                      {!f.endsWith(':') && <Check className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />}
                      <span className={f.endsWith(':') ? 'text-muted-foreground' : ''}>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* CTA final */}
      <section className="border-t bg-primary/5">
        <div className="max-w-3xl mx-auto px-6 py-24 text-center">
          <Reveal>
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-5">
              Rendez à vos ingénieurs le temps de faire de l’ingénierie.
            </h2>
            <p className="text-muted-foreground max-w-lg mx-auto mb-9">
              Créez votre compte en deux minutes et produisez vos premiers documents dès aujourd’hui.
            </p>
            <Link href="/register">
              <Button size="lg" className="gap-2 group">
                Créer mon compte
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Button>
            </Link>
          </Reveal>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t">
        <div className="max-w-6xl mx-auto px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <Logo />
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
            <a href="#tarifs" className="hover:text-foreground transition-colors">Tarifs</a>
            <a href="#modules" className="hover:text-foreground transition-colors">Modules</a>
            <Link href="/login" className="hover:text-foreground transition-colors">Se connecter</Link>
            <Link href="/legal/cgu" className="hover:text-foreground transition-colors">CGU</Link>
            <Link href="/legal/confidentialite" className="hover:text-foreground transition-colors">Confidentialité</Link>
            <Link href="/legal/mentions-legales" className="hover:text-foreground transition-colors">Mentions légales</Link>
          </div>
          <div>© {new Date().getFullYear()} LESO · Suisse romande</div>
        </div>
      </footer>
    </div>
  );
}
