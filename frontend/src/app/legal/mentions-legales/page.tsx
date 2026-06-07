export const metadata = { title: 'Mentions légales — LESO' };

export default function MentionsLegalesPage() {
  return (
    <>
      <div className="not-prose mb-8 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
        <strong>À faire relire par un juriste</strong> avant usage commercial intensif.
        Le numéro IDE sera ajouté lors de l&apos;inscription au registre du commerce
        (obligatoire dès 100 000 CHF de chiffre d&apos;affaires annuel).
      </div>

      <h1>Mentions légales</h1>

      <h2>Éditeur</h2>
      <ul>
        <li>Raison sociale : Théo Tran-van (entreprise individuelle)</li>
        <li>Forme juridique : Raison individuelle</li>
        <li>Adresse : Rue de la Gare 19, 1348 Le Brassus (VD), Suisse</li>
        <li>Numéro IDE : non applicable — entreprise individuelle non inscrite au registre du commerce (CA &lt; 100 000 CHF)</li>
        <li>Email : contact@digitran.ch</li>
        <li>Responsable de la publication : Théo Tran-van</li>
      </ul>

      <h2>Hébergement</h2>
      <p>
        Interface web hébergée par Vercel Inc. ; application serveur hébergée par Render
        (région UE — Frankfurt) ; base de données et fichiers par Supabase (région UE — Frankfurt).
      </p>

      <h2>Propriété intellectuelle</h2>
      <p>
        L&apos;ensemble des éléments de la plateforme LESO (marque, interface, code) est protégé.
        Toute reproduction non autorisée est interdite.
      </p>

      <h2>Contact</h2>
      <p>Pour toute demande : contact@digitran.ch.</p>
    </>
  );
}
