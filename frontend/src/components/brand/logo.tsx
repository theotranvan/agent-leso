import Link from 'next/link';
import { cn } from '@/lib/utils';

/**
 * Marque LESO — deux équerres entrelacées (navy + or) évoquant le L et le N
 * de « Leso », et le travail structuré d'un bureau d'études.
 *
 * Composant 100 % SVG, sans dépendance ni état : utilisable aussi bien dans un
 * composant serveur (landing) que client (sidebar).
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      role="img"
      aria-label="Logo LESO"
      className={cn('h-7 w-7', className)}
      fill="none"
      strokeWidth={10}
      strokeLinecap="butt"
    >
      {/* Équerre navy (bas-gauche) */}
      <path
        d="M 40 28 L 28 28 L 28 64 Q 28 72 36 72 L 60 72 L 60 50"
        stroke="#1C2541"
      />
      {/* Équerre or (haut-droite) — symétrique 180° */}
      <path
        d="M 60 72 L 72 72 L 72 36 Q 72 28 64 28 L 40 28 L 40 50"
        stroke="#C9A063"
      />
    </svg>
  );
}

export function Logo({
  href = '/',
  className,
  markClassName,
  withText = true,
}: {
  href?: string | null;
  className?: string;
  markClassName?: string;
  withText?: boolean;
}) {
  const content = (
    <span className={cn('flex items-center gap-2 font-semibold tracking-tight', className)}>
      <LogoMark className={markClassName} />
      {withText && <span className="text-lg">LESO</span>}
    </span>
  );
  if (href === null) return content;
  return (
    <Link href={href} className="inline-flex items-center transition-opacity hover:opacity-80">
      {content}
    </Link>
  );
}
