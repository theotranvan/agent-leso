import Link from 'next/link';
import { redirect } from 'next/navigation';
import {
  Flame, Building, Building2, Shield, Bell, ArrowRight, Check,
  Clock, FileWarning, Repeat, TrendingDown, Sparkles, FileCheck2,
  Lock, Award, ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { createServerSupabase } from '@/lib/supabase-server';

export default async function LandingPage() {
  const supabase = await createServerSupabase();
  const { data: { user } } = await supabase.auth.getUser();
  if (user) redirect('/dashboard');

  const pains = [
    {
      icon: Clock,
      title: 'Des heures perdues sur la production documentaire',
      desc: "Un CCTP complet, c'est 1 a 2 jours d'ingenieur. Une note de calcul, un demi-jour. Du temps facture a perte sur des taches repetitives au lieu de la vraie ingenierie.",
    },
    {
      icon: FileWarning,
      title: 'Le risque reglementaire qui plane en permanence',
      desc: "SIA, AEAI, Minergie, droit cantonal : les normes evoluent sans arret. Une exigence oubliee et c'est un dossier renvoye, des semaines de retard, votre credibilite en jeu.",
    },
    {
      icon: Repeat,
      title: 'Tout est a refaire a chaque affaire',
      desc: "Vos meilleurs CCTP dorment dans d'anciens dossiers. Chaque nouveau projet repart d'une page blanche, ou d'un copier-coller risque qu'il faut tout verifier.",
    },
  ];

  const modules = [
    { icon: Flame, title: 'Thermique SIA 380/1', desc: "Justificatifs Minergie, export gbXML vers Lesosai, lecture directe de vos maquettes IFC." },
    { icon: Building, title: 'Structure SIA 260-267', desc: "Notes de calcul, fichiers SAF pour Scia/RFEM, double-verification analytique automatique." },
    { icon: FileCheck2, title: 'CCTP & DPGF', desc: "Descriptifs techniques et bordereaux par lot CFC, aux prix KBOB de Suisse romande." },
    { icon: Building2, title: 'IDC & energie cantonale', desc: "Calcul OCEN, formulaires pre-remplis, extraction automatique des factures." },
    { icon: Shield, title: 'AEAI incendie', desc: "Checklists par typologie de batiment, rapports de conformite prets a deposer." },
    { icon: Bell, title: 'Veille reglementaire', desc: "Fedlex + cantons surveilles en continu. Un resume mensuel cible pour VOTRE bureau." },
  ];

  const steps = [
    { n: '01', title: 'Vous decrivez votre affaire', desc: "Adresse, surfaces, labels vises. Ou vous deposez directement votre maquette IFC : l'agent en extrait les donnees." },
    { n: '02', title: "L'agent produit le document", desc: "CCTP, note de calcul, justificatif... genere en quelques minutes, aux normes suisses en vigueur, a votre charte graphique." },
    { n: '03', title: 'Vous validez en un clic', desc: "L'IA pre-verifie et vous signale uniquement les points sensibles. Vous gardez le dernier mot — votre responsabilite, votre signature." },
  ];

  const plans = [
    {
      name: 'Starter',
      price: '690',
      tagline: 'Pour le bureau independant',
      tasks: '500 documents / mois',
      features: ['Tous les modules suisses', '1 utilisateur', '8 millions de tokens / mois', 'Documents a votre charte', 'Support par email', '10 Go de stockage'],
    },
    {
      name: 'Pro',
      price: '1 900',
      tagline: 'Pour les bureaux de 5 a 20 personnes',
      tasks: '2 000 documents / mois',
      features: ['Tout Starter, plus :', 'Utilisateurs illimites', '20 millions de tokens / mois', 'Veille reglementaire personnalisee', 'Validation deleguee (junior + responsable)', 'Vue multi-affaires (kanban)', 'Support prioritaire', '50 Go de stockage'],
      highlight: true,
    },
    {
      name: 'Enterprise',
      price: '5 000',
      tagline: 'Pour les grands bureaux',
      tasks: 'Documents illimites',
      features: ['Tout Pro, plus :', '60 millions de tokens / mois', 'SLA 99.9 %', 'Account manager dedie', 'Integrations sur mesure', 'Stockage illimite'],
    },
  ];

  const Logo = () => (
    <Link href="/" className="flex items-center gap-2 font-semibold">
      <div className="h-7 w-7 rounded-md bg-primary text-primary-foreground grid place-items-center text-sm font-bold">B</div>
      <span>LESO</span>
    </Link>
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <nav className="border-b bg-background/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <Logo />
          <div className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <a href="#probleme" className="hover:text-foreground">Pourquoi</a>
            <a href="#modules" className="hover:text-foreground">Modules</a>
            <a href="#fonctionnement" className="hover:text-foreground">Comment ca marche</a>
            <a href="#tarifs" className="hover:text-foreground">Tarifs</a>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login"><Button variant="ghost" size="sm">Se connecter</Button></Link>
            <Link href="/register"><Button size="sm">Essayer gratuitement</Button></Link>
          </div>
        </div>
      </nav>

      <section className="max-w-5xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border bg-muted/40 text-xs text-muted-foreground mb-6">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Concu pour les bureaux d'etudes techniques de Suisse romande
        </div>
        <h1 className="text-4xl md:text-6xl font-semibold tracking-tight leading-[1.05] mb-6">
          Vos dossiers techniques,<br />produits en minutes.<br />
          <span className="text-muted-foreground">Pas en jours.</span>
        </h1>
        <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-9">
          LESO redige vos CCTP, notes de calcul, justificatifs thermiques et dossiers
          reglementaires — aux normes suisses, a votre charte. Vous gardez le controle et la signature.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link href="/register">
            <Button size="lg" className="gap-2 w-full sm:w-auto">
              Demarrer gratuitement <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <a href="#fonctionnement">
            <Button size="lg" variant="outline" className="w-full sm:w-auto">Voir comment ca marche</Button>
          </a>
        </div>
        <p className="text-xs text-muted-foreground mt-5">
          Sans carte bancaire · Donnees hebergees en Suisse / UE · Vos documents restent les votres
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-16 max-w-3xl mx-auto">
          {[
            { v: '~1 jour', l: 'economise par CCTP' },
            { v: '31 normes', l: 'suisses couvertes' },
            { v: '5 min', l: 'pour un justificatif' },
            { v: '100 %', l: 'a votre charte' },
          ].map((s) => (
            <div key={s.l} className="rounded-xl border bg-muted/20 p-4">
              <div className="text-2xl font-semibold tracking-tight">{s.v}</div>
              <div className="text-xs text-muted-foreground mt-1">{s.l}</div>
            </div>
          ))}
        </div>
      </section>

      <section id="probleme" className="border-t bg-muted/10">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <h2 className="text-3xl font-semibold tracking-tight mb-3">
              Vous le savez : la valeur d'un BET n'est pas dans la paperasse.
            </h2>
            <p className="text-muted-foreground">
              Pourtant, c'est elle qui mange vos journees. Voici ce que LESO fait disparaitre.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {pains.map((p) => (
              <div key={p.title} className="rounded-2xl border bg-background p-6">
                <div className="h-11 w-11 rounded-xl bg-red-50 text-red-500 grid place-items-center mb-4">
                  <p.icon className="h-5 w-5" />
                </div>
                <h3 className="font-semibold mb-2">{p.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="fonctionnement" className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="inline-flex items-center gap-2 text-sm text-primary font-medium mb-3">
            <Sparkles className="h-4 w-4" /> La solution
          </div>
          <h2 className="text-3xl font-semibold tracking-tight mb-3">
            Trois etapes. Et le dossier est pret.
          </h2>
          <p className="text-muted-foreground">
            LESO ne vous remplace pas. Il fait le travail ingrat, vous gardez l'expertise et la decision.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {steps.map((s, i) => (
            <div key={s.n} className="relative rounded-2xl border bg-background p-6">
              <div className="text-4xl font-semibold text-muted-foreground/30 mb-3">{s.n}</div>
              <h3 className="font-semibold mb-2">{s.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
              {i < steps.length - 1 && (
                <ChevronRight className="hidden md:block absolute -right-4 top-1/2 -translate-y-1/2 h-6 w-6 text-muted-foreground/30" />
              )}
            </div>
          ))}
        </div>
      </section>

      <section id="modules" className="border-t bg-muted/10">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <h2 className="text-3xl font-semibold tracking-tight mb-3">
              Tout votre metier, couvert.
            </h2>
            <p className="text-muted-foreground">
              Du justificatif thermique au dossier incendie, chaque livrable d'un BET romand est pris en charge.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {modules.map((m) => (
              <div key={m.title} className="rounded-2xl border bg-background p-6 hover:shadow-md transition-shadow">
                <div className="h-11 w-11 rounded-xl bg-primary/10 text-primary grid place-items-center mb-4">
                  <m.icon className="h-5 w-5" />
                </div>
                <h3 className="font-semibold mb-2">{m.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{m.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 text-sm text-primary font-medium mb-3">
              <Lock className="h-4 w-4" /> Pense pour les ingenieurs, pas contre eux
            </div>
            <h2 className="text-3xl font-semibold tracking-tight mb-4">
              L'IA propose. Vous decidez. Toujours.
            </h2>
            <p className="text-muted-foreground leading-relaxed mb-6">
              Chaque document genere recoit un score de confiance. L'agent vous signale uniquement
              les points a verifier, vous ne relisez pas 40 pages pour en corriger deux. Et les
              livrables qui engagent votre responsabilite professionnelle — notes de calcul,
              justificatifs — restent toujours sous votre validation explicite.
            </p>
            <ul className="space-y-3">
              {[
                'Score de confiance IA sur chaque document',
                'Seuls les points sensibles vous sont remontes',
                'Validation en un clic, depuis votre bureau ou votre mobile',
                'Votre signature, votre responsabilite, votre charte',
              ].map((f) => (
                <li key={f} className="flex items-start gap-3 text-sm">
                  <Check className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border bg-muted/20 p-8">
            <div className="flex items-center gap-4 mb-6">
              <div className="h-14 w-14 rounded-full bg-emerald-50 text-emerald-600 grid place-items-center text-lg font-bold">94</div>
              <div>
                <div className="font-semibold">CCTP Ventilation</div>
                <div className="text-sm text-emerald-600 font-medium">Confiance elevee · pret a approuver</div>
              </div>
            </div>
            <div className="space-y-3 text-sm">
              {[
                ['Normes citees', 'SIA 382/1'],
                ['Anomalies detectees', 'Aucune'],
                ['Completude', '100 %'],
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
        </div>
      </section>

      <section className="border-t bg-primary/5">
        <div className="max-w-4xl mx-auto px-6 py-20 text-center">
          <div className="inline-flex items-center gap-2 text-sm text-primary font-medium mb-3">
            <TrendingDown className="h-4 w-4" /> Le calcul est vite fait
          </div>
          <h2 className="text-3xl font-semibold tracking-tight mb-4">
            Un seul CCTP economise par mois, et l'abonnement est deja rentabilise.
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto mb-10">
            Un dossier d'appel d'offres complet represente plusieurs jours d'ingenieur. LESO
            le produit en une fraction du temps. Le reste, c'est de la marge et des affaires
            supplementaires que vous pouvez enfin accepter.
          </p>
          <div className="grid sm:grid-cols-3 gap-6 max-w-2xl mx-auto">
            {[
              { v: '1 jour', l: "d'ingenieur economise par CCTP", sub: '≈ 1 600 CHF' },
              { v: '×4', l: 'de capacite de production', sub: 'sans recruter' },
              { v: '90 %', l: 'de marge sur chaque dossier', sub: 'automatise' },
            ].map((s) => (
              <div key={s.l} className="rounded-2xl border bg-background p-6">
                <div className="text-3xl font-semibold tracking-tight text-primary">{s.v}</div>
                <div className="text-sm mt-2">{s.l}</div>
                <div className="text-xs text-muted-foreground mt-1">{s.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="tarifs" className="max-w-6xl mx-auto px-6 py-20">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <h2 className="text-3xl font-semibold tracking-tight mb-3">Un tarif simple, rentable des la premiere affaire.</h2>
          <p className="text-muted-foreground">
            Tous les modules sont inclus dans chaque plan. Vous ne payez que pour le volume.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6 items-start">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-2xl border p-7 relative ${plan.highlight ? 'border-primary shadow-lg md:scale-105 bg-background' : 'bg-background'}`}
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
                  Commencer avec {plan.name}
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
          ))}
        </div>
        <p className="text-center text-sm text-muted-foreground mt-10">
          Besoin d'un volume superieur ? Des packs de credits complementaires sont disponibles a tout moment.
        </p>
      </section>

      <section className="border-t bg-muted/10">
        <div className="max-w-4xl mx-auto px-6 py-16 text-center">
          <div className="inline-flex items-center gap-2 text-sm text-amber-600 font-medium mb-3">
            <Award className="h-4 w-4" /> Bonus
          </div>
          <h2 className="text-2xl font-semibold tracking-tight mb-3">
            Devenez un bureau certifie LESO
          </h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Affichez sur votre site et vos offres que vos dossiers sont produits et verifies avec
            un outil reconnu. Un argument de confiance de plus face a vos maitres d'ouvrage.
          </p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-24 text-center">
        <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-5">
          Rendez a vos ingenieurs ce qui leur appartient :<br />le temps de faire de l'ingenierie.
        </h2>
        <p className="text-muted-foreground max-w-xl mx-auto mb-9">
          Creez votre compte en deux minutes. Aucune carte bancaire. Vos premiers documents
          des aujourd'hui.
        </p>
        <Link href="/register">
          <Button size="lg" className="gap-2">
            Demarrer gratuitement <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </section>

      <footer className="border-t">
        <div className="max-w-6xl mx-auto px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
          <Logo />
          <div className="flex items-center gap-6">
            <a href="#tarifs" className="hover:text-foreground">Tarifs</a>
            <a href="#modules" className="hover:text-foreground">Modules</a>
            <Link href="/login" className="hover:text-foreground">Se connecter</Link>
          </div>
          <div>© {new Date().getFullYear()} LESO · Suisse romande</div>
        </div>
      </footer>
    </div>
  );
}
