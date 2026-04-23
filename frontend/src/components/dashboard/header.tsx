'use client';
import Link from 'next/link';
import { Plus, Bell } from 'lucide-react';
import { ProjectSwitcher } from './project-switcher';
import { Button } from '@/components/ui/button';

export function DashboardHeader() {
  return (
    <header className="h-14 border-b bg-background/80 backdrop-blur sticky top-0 z-30 flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <ProjectSwitcher />
      </div>
      <div className="flex items-center gap-2">
        <Link href="/veille">
          <Button variant="ghost" size="sm" className="gap-2">
            <Bell className="h-4 w-4" />
            <span className="hidden sm:inline">Alertes</span>
          </Button>
        </Link>
        <Link href="/tasks/new">
          <Button size="sm" className="gap-2">
            <Plus className="h-4 w-4" />
            Nouvelle tâche
          </Button>
        </Link>
      </div>
    </header>
  );
}
