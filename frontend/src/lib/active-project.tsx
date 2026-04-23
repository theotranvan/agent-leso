'use client';
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

export type ActiveProject = {
  id: string;
  name: string;
  canton?: string;
  address?: string;
  affectation?: string;
} | null;

interface ActiveProjectContextValue {
  activeProject: ActiveProject;
  setActiveProject: (p: ActiveProject) => void;
}

const ActiveProjectContext = createContext<ActiveProjectContextValue | null>(null);

const STORAGE_KEY = 'bet_active_project_v1';

export function ActiveProjectProvider({ children }: { children: ReactNode }) {
  const [activeProject, setActiveProjectState] = useState<ActiveProject>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        setActiveProjectState(JSON.parse(raw));
      }
    } catch {
      /* ignore */
    }
    setHydrated(true);
  }, []);

  const setActiveProject = (p: ActiveProject) => {
    setActiveProjectState(p);
    try {
      if (p) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      /* ignore */
    }
  };

  // Évite le flash : ne rend rien tant qu'on n'a pas hydraté localStorage côté client
  if (!hydrated) {
    return <ActiveProjectContext.Provider value={{ activeProject: null, setActiveProject }}>
      {children}
    </ActiveProjectContext.Provider>;
  }

  return (
    <ActiveProjectContext.Provider value={{ activeProject, setActiveProject }}>
      {children}
    </ActiveProjectContext.Provider>
  );
}

export function useActiveProject() {
  const ctx = useContext(ActiveProjectContext);
  if (!ctx) throw new Error('useActiveProject must be used within ActiveProjectProvider');
  return ctx;
}
