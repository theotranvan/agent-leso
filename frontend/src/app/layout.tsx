import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'LESO — Vos dossiers techniques, produits en minutes',
    template: '%s · LESO',
  },
  description:
    "L'agent IA des bureaux d'études romands : CCTP, notes de calcul et justificatifs aux normes suisses, à votre charte. Vous gardez le contrôle et la signature.",
  icons: { icon: '/icon.svg' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
