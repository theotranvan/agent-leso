export const metadata = { title: 'Politique de confidentialité — LESO' };

export default function ConfidentialitePage() {
  return (
    <>
      <div className="not-prose mb-8 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
        <strong>À faire relire par un juriste</strong> avant usage commercial intensif.
        Texte conforme à l&apos;esprit de la LPD (nLPD suisse) et du RGPD.
      </div>

      <h1>Politique de confidentialité</h1>
      <p>Dernière mise à jour : 7 juin 2026. Responsable du traitement : Théo Tran-van (entreprise individuelle), Rue de la Gare 19, 1348 Le Brassus (VD), Suisse.</p>

      <h2>1. Données traitées</h2>
      <ul>
        <li><strong>Compte</strong> : nom, email, organisation, rôle.</li>
        <li><strong>Données de projet</strong> : informations et documents que vous importez (plans, IFC, PDF, métrés, paramètres).</li>
        <li><strong>Données d&apos;usage</strong> : journaux techniques, consommation, audit des actions (validation, etc.).</li>
        <li><strong>Facturation</strong> : données nécessaires gérées par notre prestataire de paiement.</li>
      </ul>

      <h2>2. Finalités</h2>
      <ul>
        <li>Fournir et sécuriser le service (génération de livrables, validation, stockage).</li>
        <li>Gérer les comptes, la facturation et le support.</li>
        <li>Améliorer la fiabilité et la performance de la plateforme.</li>
      </ul>

      <h2>3. Base légale</h2>
      <p>Exécution du contrat, intérêt légitime au bon fonctionnement et à la sécurité, et respect d&apos;obligations légales.</p>

      <h2>4. Hébergement et localisation des données</h2>
      <p>
        Les données sont hébergées chez nos sous-traitants techniques dans l&apos;Union européenne
        (région Frankfurt) et/ou en Suisse. La liste des sous-traitants comprend
        notamment : Supabase (base de données PostgreSQL et stockage des fichiers, région Frankfurt),
        Render (application serveur, région Frankfurt), Vercel (hébergement de l&apos;interface web),
        Stripe (paiement), Resend (emails),
        Anthropic et OpenAI (traitement par modèles d&apos;IA des contenus soumis pour génération).
      </p>

      <h2>5. Traitement par intelligence artificielle</h2>
      <p>
        La génération de livrables transmet le contenu nécessaire à des fournisseurs de modèles
        d&apos;IA. Ces fournisseurs (Anthropic, OpenAI) sont engagés, selon leurs conditions
        d&apos;utilisation API, à ne pas utiliser les contenus transmis pour entraîner leurs modèles.
      </p>

      <h2>6. Durée de conservation</h2>
      <p>
        Les données sont conservées pendant la durée de la relation contractuelle, puis supprimées
        ou archivées selon les obligations légales applicables. Vous pouvez demander la
        suppression de votre compte et des données associées.
      </p>

      <h2>7. Sécurité</h2>
      <ul>
        <li>Cloisonnement strict des données par organisation (multi-tenant, contrôle d&apos;accès au niveau de la base).</li>
        <li>Chiffrement des échanges (HTTPS) et des données au repos chez nos hébergeurs.</li>
        <li>Journalisation des accès et des validations.</li>
      </ul>

      <h2>8. Vos droits</h2>
      <p>
        Conformément à la LPD et au RGPD, vous disposez d&apos;un droit d&apos;accès, de
        rectification, d&apos;effacement, de limitation, d&apos;opposition et de portabilité.
        Pour les exercer : contact@digitran.ch. Vous pouvez aussi saisir l&apos;autorité compétente
        (PFPDT en Suisse).
      </p>

      <h2>9. Cookies</h2>
      <p>
        La plateforme utilise uniquement les cookies strictement nécessaires à l&apos;authentification
        et au fonctionnement. Aucun cookie de mesure d&apos;audience ou de publicité n&apos;est utilisé.
      </p>

      <h2>10. Contact</h2>
      <p>Pour toute question relative à vos données : contact@digitran.ch.</p>
    </>
  );
}
