'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard, FolderKanban, CreditCard, Settings, LogOut, Sparkles,
  Flame, Building, Layers, Building2, Bell, Shield, ShieldCheck,
  Ruler, ClipboardCheck, BarChart3, KanbanSquare, Award,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { createClient } from '@/lib/supabase';
import { Button } from '@/components/ui/button';
import { Logo } from '@/components/brand/logo';

// 1. Le quotidien : par où on commence
const navStart = [
  { href: '/dashboard', label: 'Accueil', icon: LayoutDashboard },
  { href: '/projects', label: 'Mes projets', icon: FolderKanban },
  { href: '/tasks/new', label: 'Générer un livrable', icon: Sparkles },
];

// 2. Les outils métier dédiés (interfaces riches, au-delà du formulaire générique)
const navTools = [
  { href: '/thermique', label: 'Thermique SIA', icon: Flame },
  { href: '/structure', label: 'Structure SIA', icon: Building },
  { href: '/idc', label: 'IDC Genève', icon: Building2 },
  { href: '/aeai', label: 'AEAI (incendie)', icon: Shield },
  { href: '/metres', label: 'Métrés IFC', icon: Ruler },
  { href: '/bim', label: 'Pré-BIM', icon: Layers },
];

// 3. Suivi : ce qui est en cours, à valider, à surveiller
const navTrack = [
  { href: '/board', label: 'Mes affaires', icon: KanbanSquare },
  { href: '/validation', label: 'À valider', icon: ClipboardCheck },
  { href: '/compliance', label: 'Conformité', icon: ShieldCheck },
  { href: '/veille', label: 'Veille romande', icon: Bell },
];

// 4. Compte
const navAccount = [
  { href: '/analytics', label: 'Statistiques', icon: BarChart3 },
  { href: '/certification', label: 'Certification', icon: Award },
  { href: '/billing', label: 'Facturation', icon: CreditCard },
  { href: '/settings', label: 'Paramètres', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push('/login');
    router.refresh();
  };

  return (
    <aside className="hidden md:flex w-60 flex-col border-r bg-background">
      <div className="flex h-14 items-center border-b px-6">
        <Logo href="/dashboard" />
      </div>
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        <NavSection items={navStart} pathname={pathname} />
        <NavLabel>Outils métier</NavLabel>
        <NavSection items={navTools} pathname={pathname} />
        <NavLabel>Suivi</NavLabel>
        <NavSection items={navTrack} pathname={pathname} />
        <NavLabel>Compte</NavLabel>
        <NavSection items={navAccount} pathname={pathname} />
      </nav>
      <div className="border-t p-3">
        <Button variant="ghost" className="w-full justify-start text-muted-foreground" onClick={handleLogout}>
          <LogOut className="h-4 w-4 mr-3" />
          Déconnexion
        </Button>
      </div>
    </aside>
  );
}


function NavLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-5 mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
      {children}
    </p>
  );
}

function NavSection({
  items,
  pathname,
}: {
  items: Array<{ href: string; label: string; icon: any }>;
  pathname: string;
}) {
  return (
    <ul className="space-y-1">
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground',
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
