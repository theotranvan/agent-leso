export const metadata = { title: 'Mentions légales — LESO' };

export default function MentionsLegalesPage() {
  return (
    <>
      <div className="not-prose mb-8 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
        <strong>Modèle à compléter.</strong> Renseignez votre raison sociale, votre numéro IDE
        et vos coordonnées avant mise en production.
      </div>

      <h1>Mentions légales</h1>

      <h2>Éditeur</h2>
      <ul>
        <li>Raison sociale : [Raison sociale]</li>
        <li>Forme juridique : [SA / Sàrl / raison individuelle]</li>
        <li>Adresse : [adresse complète], Suisse</li>
        <li>Numéro IDE : [CHE-xxx.xxx.xxx]</li>
        <li>Email : [email de contact]</li>
        <li>Responsable de la publication : [nom]</li>
      </ul>

      <h2>Hébergement</h2>
      <p>
        Application hébergée par [Vercel Inc.] ; base de données et fichiers par [Supabase],
        région [UE — Frankfurt, à confirmer].
      </p>

      <h2>Propriété intellectuelle</h2>
      <p>
        L&apos;ensemble des éléments de la plateforme LESO (marque, interface, code) est protégé.
        Toute reproduction non autorisée est interdite.
      </p>

      <h2>Contact</h2>
      <p>Pour toute demande : [email de contact].</p>
    </>
  );
}
