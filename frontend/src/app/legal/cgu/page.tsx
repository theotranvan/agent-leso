export const metadata = { title: 'Conditions générales d\'utilisation — LESO' };

export default function CguPage() {
  return (
    <>
      <div className="not-prose mb-8 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
        <strong>Modèle à faire valider par un juriste.</strong> Ce texte est une base de
        travail à adapter à votre raison sociale et à faire relire avant mise en production.
        Les éléments entre crochets <code>[…]</code> doivent être complétés.
      </div>

      <h1>Conditions générales d&apos;utilisation</h1>
      <p>Dernière mise à jour : [date]. Éditeur : [Raison sociale], [adresse], Suisse (ci-après « LESO »).</p>

      <h2>1. Objet</h2>
      <p>
        Les présentes conditions régissent l&apos;accès et l&apos;utilisation de la plateforme
        LESO, un logiciel en ligne (SaaS) d&apos;assistance à la production de livrables
        techniques pour les bureaux d&apos;études et professionnels de la construction en Suisse.
      </p>

      <h2>2. Nature du service et responsabilité professionnelle</h2>
      <p>
        LESO est un outil d&apos;aide à la rédaction et au calcul. Les documents générés
        (CCTP, justificatifs, notes, rapports, métrés, chiffrages, etc.) sont des
        <strong> projets de livrables</strong> qui doivent être vérifiés, complétés et validés
        par un professionnel qualifié avant toute diffusion ou dépôt officiel. LESO ne se
        substitue pas au jugement de l&apos;ingénieur ou de l&apos;architecte responsable et
        n&apos;assume aucune responsabilité quant à l&apos;exactitude réglementaire ou technique
        des documents produits, qui restent sous la responsabilité de l&apos;utilisateur.
      </p>

      <h2>3. Compte et accès</h2>
      <ul>
        <li>L&apos;utilisateur est responsable de la confidentialité de ses identifiants.</li>
        <li>Chaque organisation gère ses membres et leurs rôles (administrateur, ingénieur, lecteur).</li>
        <li>LESO peut suspendre un accès en cas d&apos;usage abusif ou contraire aux présentes.</li>
      </ul>

      <h2>4. Abonnement, quotas et facturation</h2>
      <p>
        L&apos;accès est fourni selon la formule souscrite. La consommation peut être encadrée
        par un quota (jetons/tokens). La facturation est gérée via notre prestataire de paiement
        [Stripe]. Les conditions tarifaires, la durée et les modalités de résiliation sont
        précisées lors de la souscription.
      </p>

      <h2>5. Propriété intellectuelle</h2>
      <p>
        LESO conserve l&apos;ensemble des droits sur la plateforme. L&apos;utilisateur conserve
        la propriété des contenus qu&apos;il importe et des livrables qu&apos;il produit et valide.
      </p>

      <h2>6. Disponibilité</h2>
      <p>
        LESO met en œuvre des moyens raisonnables pour assurer la disponibilité du service mais
        ne garantit pas une absence totale d&apos;interruption. Les éventuels engagements de niveau
        de service (SLA) figurent dans le contrat applicable.
      </p>

      <h2>7. Protection des données</h2>
      <p>
        Le traitement des données personnelles est décrit dans notre{' '}
        <a href="/legal/confidentialite">politique de confidentialité</a>.
      </p>

      <h2>8. Limitation de responsabilité</h2>
      <p>
        Dans les limites permises par le droit applicable, la responsabilité de LESO est limitée
        aux dommages directs et plafonnée au montant des sommes versées au cours des 12 derniers
        mois. LESO n&apos;est pas responsable des dommages indirects.
      </p>

      <h2>9. Droit applicable et for</h2>
      <p>
        Les présentes sont soumises au droit suisse. Le for exclusif est à [siège de l&apos;éditeur],
        sous réserve des dispositions impératives.
      </p>

      <h2>10. Contact</h2>
      <p>Pour toute question : [email de contact].</p>
    </>
  );
}
