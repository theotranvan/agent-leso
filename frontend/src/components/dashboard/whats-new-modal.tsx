'use client';
import { useEffect, useState } from 'react';
import { Check, Sparkles, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { WHATS_NEW, type WhatsNewEntry } from '@/lib/whats-new';

// Mémorise (sur le navigateur) la dernière nouveauté vue par l'utilisateur.
const SEEN_KEY = 'leso_whatsnew_seen_v1';

/**
 * Pop-up « Quoi de neuf » affiché à la reconnexion lorsqu'il y a eu des
 * nouveautés depuis la dernière visite. Purement côté navigateur : aucune
 * donnée serveur, ne s'affiche qu'une fois par mise à jour.
 */
export function WhatsNewModal() {
  const [open, setOpen] = useState(false);
  const [entries, setEntries] = useState<WhatsNewEntry[]>([]);

  useEffect(() => {
    if (WHATS_NEW.length === 0) return;
    let seen: string | null = null;
    try {
      seen = window.localStorage.getItem(SEEN_KEY);
    } catch {
      /* mode privé / quota : on affichera la nouveauté, sans pouvoir la mémoriser */
    }

    const latestId = WHATS_NEW[0].id;
    if (seen === latestId) return; // déjà à jour

    // Entrées non encore vues = toutes celles situées au-dessus de la dernière vue.
    let unseen = WHATS_NEW;
    if (seen) {
      const idx = WHATS_NEW.findIndex((e) => e.id === seen);
      unseen = idx === -1 ? WHATS_NEW : WHATS_NEW.slice(0, idx);
    }
    if (unseen.length === 0) return;

    setEntries(unseen);
    setOpen(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dismiss();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const dismiss = () => {
    try {
      window.localStorage.setItem(SEEN_KEY, WHATS_NEW[0].id);
    } catch {
      /* ignore */
    }
    setOpen(false);
  };

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px] animate-in fade-in duration-200"
        onClick={dismiss}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="whatsnew-title"
        className="fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-[92vw] max-w-lg -translate-x-1/2 -translate-y-1/2 flex-col rounded-2xl border bg-card shadow-2xl animate-in fade-in zoom-in-95 duration-200"
      >
        {/* En-tête */}
        <div className="flex items-start justify-between gap-3 p-5 border-b">
          <div className="flex items-center gap-3">
            <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2 id="whatsnew-title" className="font-semibold text-base leading-tight">
                Quoi de neuf sur LESO
              </h2>
              <p className="text-sm text-muted-foreground mt-0.5">
                Les nouveautés depuis votre dernière visite
              </p>
            </div>
          </div>
          <button
            onClick={dismiss}
            aria-label="Fermer"
            className="p-1 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Corps */}
        <div className="overflow-y-auto p-5 space-y-6">
          {entries.map((entry) => (
            <div key={entry.id} className="space-y-3">
              <div className="flex items-baseline gap-2">
                <span className="text-sm font-medium">{entry.title}</span>
                <span className="text-xs text-muted-foreground">· {entry.date}</span>
              </div>
              <ul className="space-y-2.5">
                {entry.items.map((item, i) => (
                  <li key={i} className="flex gap-2.5 text-sm leading-relaxed">
                    <Check className="h-4 w-4 mt-0.5 shrink-0 text-emerald-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Pied */}
        <div className="flex justify-end p-4 border-t">
          <Button onClick={dismiss}>J’ai compris</Button>
        </div>
      </div>
    </>
  );
}
