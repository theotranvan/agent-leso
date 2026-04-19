'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard, FolderKanban, ListChecks, CreditCard, Settings, LogOut, Sparkles,
  Flame, Building, Layers, Building2, Bell, BookOpen, Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { createClient } from '@/lib/supabase';
import { Button } from '@/components/ui/button';

const navGeneral = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/projects', label: 'Projets', icon: FolderKanban },
  { href: '/tasks/new', label: 'Nouvelle tâche', icon: Sparkles },
];

const navCH = [
  { href: '/thermique', label: 'Thermique SIA', icon: Flame },
  { href: '/structure', label: 'Structure SIA', icon: Building },
  { href: '/bim', label: 'Pré-BIM', icon: Layers },
  { href: '/idc', label: 'IDC Genève', icon: Building2 },
  { href: '/aeai', label: 'AEAI (incendie)', icon: Shield },
  { href: '/veille', label: 'Veille CH', icon: Bell },
];

const navAccount = [
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
        <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
          <div className="h-7 w-7 rounded-md bg-primary text-primary-foreground grid place-items-center text-sm font-bold">B</div>
          <span>BET Agent</span>
        </Link>
      </div>
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        <NavSection items={navGeneral} pathname={pathname} />
        <p className="mt-5 mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Suisse romande
        </p>
        <NavSection items={navCH} pathname={pathname} />
        <p className="mt-5 mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Compte
        </p>
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
