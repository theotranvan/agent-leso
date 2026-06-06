export const metadata = { title: 'Politique de confidentialité — LESO' };

export default function ConfidentialitePage() {
  return (
    <>
      <div className="not-prose mb-8 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
        <strong>Modèle à faire valider par un juriste.</strong> Base de travail conforme à
        l&apos;esprit de la LPD (nLPD suisse) et du RGPD. À adapter à votre hébergement réel et
        à faire relire avant mise en production. Les éléments entre crochets <code>[…]</code> sont à compléter.
      </div>

      <h1>Politique de confidentialité</h1>
      <p>Dernière mise à jour : [date]. Responsable du traitement : [Raison sociale], [adresse], Suisse.</p>

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
        [région : Frankfurt — à confirmer] et/ou en Suisse. La liste des sous-traitants comprend
        notamment : [Supabase/PostgreSQL] (base de données et stockage des fichiers),
        [Vercel] (hébergement de l&apos;application), [Stripe] (paiement), [Resend] (emails),
        [Anthropic / OpenAI] (traitement par modèles d&apos;IA des contenus soumis pour génération).
      </p>

      <h2>5. Traitement par intelligence artificielle</h2>
      <p>
        La génération de livrables transmet le contenu nécessaire à des fournisseurs de modèles
        d&apos;IA. Ces fournisseurs sont engagés par contrat à ne pas utiliser vos contenus pour
        entraîner leurs modèles [à confirmer selon les conditions du fournisseur retenu].
      </p>

      <h2>6. Durée de conservation</h2>
      <p>
        Les données sont conservées pendant la durée de la relation contractuelle, puis archivées
        ou supprimées selon les obligations légales [durée à préciser]. Vous pouvez demander la
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
        Pour les exercer : [email de contact]. Vous pouvez aussi saisir l&apos;autorité compétente
        (PFPDT en Suisse).
      </p>

      <h2>9. Cookies</h2>
      <p>
        La plateforme utilise les cookies strictement nécessaires à l&apos;authentification et au
        fonctionnement. [Compléter si des cookies de mesure d&apos;audience sont ajoutés.]
      </p>

      <h2>10. Contact</h2>
      <p>Pour toute question relative à vos données : [email de contact].</p>
    </>
  );
}
