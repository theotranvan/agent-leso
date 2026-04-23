'use client';
import { useEffect, useRef, useState } from 'react';
import { ChevronDown, Check, FolderKanban, Search, Plus } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import { useActiveProject, type ActiveProject } from '@/lib/active-project';

export function ProjectSwitcher() {
  const { activeProject, setActiveProject } = useActiveProject();
  const [open, setOpen] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Load projects when opening
  useEffect(() => {
    if (!open || projects.length > 0) return;
    setLoading(true);
    api.projects.list()
      .then((r: any) => setProjects(r.projects || []))
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
  }, [open, projects.length]);

  const filtered = projects.filter(p =>
    !query || p.name.toLowerCase().includes(query.toLowerCase()) ||
    (p.address || '').toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (p: any) => {
    setActiveProject({
      id: p.id, name: p.name, canton: p.canton,
      address: p.address, affectation: p.affectation,
    });
    setOpen(false);
  };

  const handleClear = () => {
    setActiveProject(null);
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          'flex items-center gap-2.5 pl-3 pr-2 py-1.5 rounded-md text-sm transition-colors',
          'border bg-card hover:bg-accent/50 focus-ring',
          activeProject ? 'border-border' : 'border-dashed border-muted-foreground/30',
        )}
      >
        <FolderKanban className="h-3.5 w-3.5 text-muted-foreground" />
        {activeProject ? (
          <>
            <span className="font-medium truncate max-w-[200px]">{activeProject.name}</span>
            {activeProject.canton && (
              <span className="text-xs text-muted-foreground">· {activeProject.canton}</span>
            )}
          </>
        ) : (
          <span className="text-muted-foreground">Aucun projet sélectionné</span>
        )}
        <ChevronDown className={cn('h-3.5 w-3.5 text-muted-foreground transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1.5 w-80 rounded-lg border bg-card shadow-lg z-50 overflow-hidden">
          <div className="p-2 border-b">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="text"
                placeholder="Rechercher un projet..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full h-8 pl-8 pr-2 rounded-md bg-muted text-sm focus-ring border-0"
                autoFocus
              />
            </div>
          </div>

          <div className="max-h-72 overflow-y-auto">
            {loading ? (
              <div className="px-3 py-4 text-center text-xs text-muted-foreground">Chargement…</div>
            ) : filtered.length === 0 ? (
              <div className="px-3 py-6 text-center">
                <p className="text-sm text-muted-foreground mb-2">
                  {query ? 'Aucun projet correspondant' : 'Aucun projet'}
                </p>
                <Link
                  href="/projects"
                  onClick={() => setOpen(false)}
                  className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                >
                  <Plus className="h-3 w-3" /> Créer un projet
                </Link>
              </div>
            ) : (
              <ul>
                {filtered.map((p) => {
                  const isActive = activeProject?.id === p.id;
                  return (
                    <li key={p.id}>
                      <button
                        onClick={() => handleSelect(p)}
                        className={cn(
                          'w-full flex items-start gap-2 px-3 py-2 text-left text-sm hover:bg-accent transition-colors',
                          isActive && 'bg-accent/60',
                        )}
                      >
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate">{p.name}</p>
                          <p className="text-xs text-muted-foreground truncate">
                            {p.canton && <span>{p.canton} · </span>}
                            {p.address || p.affectation || 'Projet'}
                          </p>
                        </div>
                        {isActive && <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-0.5" />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {activeProject && (
            <div className="border-t p-2">
              <button
                onClick={handleClear}
                className="w-full text-xs text-muted-foreground hover:text-foreground py-1 rounded-md hover:bg-muted transition-colors"
              >
                Désélectionner le projet actif
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
