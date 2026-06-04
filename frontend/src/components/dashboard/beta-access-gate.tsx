'use client';
import { useEffect, useState } from 'react';
import { Lock, Mail } from 'lucide-react';
import { api } from '@/lib/api';

const FALLBACK_CONTACT = 'theo.cours34@gmail.com';

/**
 * Garde d'accès bêta.
 *
 * Pendant la phase pilote, un compte doit avoir un forfait actif (`active === true`)
 * pour utiliser l'outil. Un nouveau compte est créé inactif côté backend ; tant
 * qu'il n'est pas activé, on remplace le contenu par un écran d'attente d'activation.
 *
 * Principe « fail-open » : on ne bloque QUE si l'API renvoie explicitement
 * `active === false`. En cas d'erreur réseau / endpoint indisponible, on laisse
 * passer — il est hors de question de verrouiller par erreur un compte déjà actif
 * (ex. les ingénieurs du pilote Conti).
 */
export function BetaAccessGate({ children }: { children: React.ReactNode }) {
  const [blocked, setBlocked] = useState(false);
  const [contact, setContact] = useState(FALLBACK_CONTACT);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .getBillingStatus()
      .then((s: any) => {
        if (cancelled) return;
        if (s?.billing_contact) setContact(s.billing_contact);
        // On bloque uniquement sur une réponse explicite active === false.
        if (s && s.active === false) setBlocked(true);
      })
      .catch(() => {
        /* fail-open : on ne bloque jamais sur une erreur */
      })
      .finally(() => {
        if (!cancelled) setChecked(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Tant qu'on n'a pas la réponse, on affiche le contenu (évite un flash de blocage
  // pour les comptes actifs, qui sont la majorité).
  if (!checked || !blocked) return <>{children}</>;

  return (
    <div className="mx-auto max-w-lg py-16 text-center">
      <div className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-full bg-muted">
        <Lock className="h-6 w-6 text-muted-foreground" />
      </div>
      <h1 className="text-xl font-semibold tracking-tight">Compte en attente d'activation</h1>
      <p className="mt-3 text-sm text-muted-foreground">
        LESO est en version bêta. Pour démarrer, un forfait doit être activé sur votre
        organisation. Le paiement en ligne sera ouvert prochainement — pendant la bêta,
        l'activation se fait directement avec nous.
      </p>
      <a
        href={`mailto:${contact}?subject=${encodeURIComponent('Activation forfait LESO')}`}
        className="mt-6 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90"
      >
        <Mail className="h-4 w-4" />
        Demander l'activation
      </a>
      <p className="mt-4 text-xs text-muted-foreground">
        ou écrivez à <span className="font-medium text-foreground">{contact}</span>
      </p>
    </div>
  );
}
