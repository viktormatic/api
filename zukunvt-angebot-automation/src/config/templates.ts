/**
 * zukunvt Proposal Structure Templates
 * Defines the 5-page standard proposal structure and formatting
 */

export interface ProposalSection {
  id: string;
  title: Record<'DE' | 'IT' | 'EN', string>;
  page: number;
  required: boolean;
  description: string;
}

export const PROPOSAL_SECTIONS: ProposalSection[] = [
  {
    id: 'cover_letter',
    title: {
      DE: 'Anschreiben',
      IT: 'Lettera di presentazione',
      EN: 'Cover Letter',
    },
    page: 1,
    required: true,
    description: 'Personal, collaborative opening referencing discovery call',
  },
  {
    id: 'legal_notice',
    title: {
      DE: 'Rechtlicher Hinweis',
      IT: 'Avviso legale',
      EN: 'Legal Notice',
    },
    page: 2,
    required: true,
    description: 'Terms, validity (6 weeks), IP rights, cost overrun policy',
  },
  {
    id: 'calculation',
    title: {
      DE: 'Kalkulation',
      IT: 'Calcolo',
      EN: 'Calculation',
    },
    page: 3,
    required: true,
    description: 'Detailed pricing table with project phases',
  },
  {
    id: 'summary',
    title: {
      DE: 'Zusammenfassung & Konditionen',
      IT: 'Riepilogo e condizioni',
      EN: 'Summary & Terms',
    },
    page: 4,
    required: true,
    description: 'Payment terms, inclusions/exclusions, total with VAT, signatures',
  },
  {
    id: 'references',
    title: {
      DE: 'Partner-Referenzen',
      IT: 'Referenze partner',
      EN: 'Partner References',
    },
    page: 5,
    required: true,
    description: '3-5 industry-relevant references and testimonials',
  },
];

/**
 * Google Docs formatting constants
 */
export const DOC_FORMATTING = {
  font: 'Roboto',
  colors: {
    primary: '#0000FF',     // zukunvt Blue
    text: '#1A1A1A',
    headerBg: '#F0F0F0',
    white: '#FFFFFF',
  },
  pageFormat: 'A4',
  margins: {
    top: 72,    // 1 inch in points
    bottom: 72,
    left: 72,
    right: 72,
  },
  fontSize: {
    title: 24,
    heading1: 18,
    heading2: 14,
    body: 11,
    small: 9,
  },
  footer: {
    text: 'zukunvt GmbH | partner.zukunvt.it | hello@zukunvt.com',
  },
} as const;

/**
 * Legal notice template content
 */
export const LEGAL_TEMPLATES: Record<'DE' | 'IT' | 'EN', {
  validity: string;
  copyright: string;
  costOverrun: string;
  agb: string;
}> = {
  DE: {
    validity: 'Dieses Angebot ist 6 Wochen ab Erhalt gültig.',
    copyright: 'Alle im Rahmen dieses Projekts erstellten Werke und Materialien bleiben bis zur vollständigen Bezahlung im Eigentum der zukunvt GmbH. Nach vollständiger Bezahlung gehen die vereinbarten Nutzungsrechte an den Partner über.',
    costOverrun: 'Kostenüberschreitungen bis zu 15% des vereinbarten Projektbudgets sind automatisch genehmigt und werden im Rahmen der regulären Abrechnung fakturiert. Bei absehbaren Überschreitungen von mehr als 15% erfolgt eine rechtzeitige Benachrichtigung und Abstimmung mit dem Partner.',
    agb: 'Es gelten die Allgemeinen Geschäftsbedingungen der zukunvt GmbH in der jeweils gültigen Fassung.',
  },
  IT: {
    validity: 'Questa offerta è valida per 6 settimane dalla ricezione.',
    copyright: 'Tutti i lavori e i materiali creati nell\'ambito di questo progetto rimangono di proprietà di zukunvt GmbH fino al completo pagamento. Dopo il pagamento completo, i diritti d\'uso concordati vengono trasferiti al partner.',
    costOverrun: 'Gli sforamenti dei costi fino al 15% del budget concordato sono automaticamente approvati. Per sforamenti superiori al 15%, verrà fornita una notifica tempestiva e concordata con il partner.',
    agb: 'Si applicano i Termini e Condizioni Generali di zukunvt GmbH nella versione vigente.',
  },
  EN: {
    validity: 'This proposal is valid for 6 weeks from receipt.',
    copyright: 'All works and materials created within the scope of this project remain the property of zukunvt GmbH until full payment. Upon full payment, the agreed usage rights are transferred to the partner.',
    costOverrun: 'Cost overruns of up to 15% of the agreed project budget are automatically approved. For anticipated overruns exceeding 15%, timely notification and coordination with the partner will be provided.',
    agb: 'The General Terms and Conditions of zukunvt GmbH apply in their current version.',
  },
};

/**
 * Industry-specific reference data for proposals
 */
export const INDUSTRY_REFERENCES: Record<string, string[]> = {
  'Technology': ['SaaS & Tech clients', 'Digital transformation projects', 'AI implementation cases'],
  'Tourism': ['Destination marketing', 'Hotel & hospitality branding', 'Tourism board campaigns'],
  'Public Sector': ['Government communications', 'Public institution branding', 'Citizen engagement'],
  'B2B': ['Industrial marketing', 'Professional services branding', 'B2B lead generation'],
  'Retail': ['E-commerce strategies', 'Omnichannel marketing', 'Retail brand development'],
  'Healthcare': ['Health sector communications', 'Medical branding', 'Patient engagement'],
  'Education': ['Educational institution branding', 'Enrollment marketing', 'EdTech partnerships'],
  'Professional Services': ['Law firm marketing', 'Consulting firm branding', 'Professional positioning'],
};

/**
 * Signature process instructions
 */
export const SIGNATURE_TEMPLATE: Record<'DE' | 'IT' | 'EN', {
  agreementText: string;
  signatureLabels: { agency: string; partner: string };
  dateLabel: string;
  placeLabel: string;
}> = {
  DE: {
    agreementText: 'Mit der Unterzeichnung dieses Angebots erkläre ich mich mit den oben genannten Konditionen und den AGB der zukunvt GmbH einverstanden.',
    signatureLabels: {
      agency: 'zukunvt GmbH',
      partner: 'Partner',
    },
    dateLabel: 'Datum',
    placeLabel: 'Ort',
  },
  IT: {
    agreementText: 'Con la firma di questa offerta, dichiaro di accettare le condizioni sopra indicate e i Termini e Condizioni Generali di zukunvt GmbH.',
    signatureLabels: {
      agency: 'zukunvt GmbH',
      partner: 'Partner',
    },
    dateLabel: 'Data',
    placeLabel: 'Luogo',
  },
  EN: {
    agreementText: 'By signing this proposal, I agree to the above terms and the General Terms and Conditions of zukunvt GmbH.',
    signatureLabels: {
      agency: 'zukunvt GmbH',
      partner: 'Partner',
    },
    dateLabel: 'Date',
    placeLabel: 'Place',
  },
};
