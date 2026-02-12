/**
 * Proposal Data Model
 * Complete typed representation of a zukunvt proposal
 */

import { Language } from './client-data';
import { ProjectPhase } from './project-phase';

export interface ProposalCalculationRow {
  /** Row number */
  nr: number;
  /** Phase/item title */
  title: string;
  /** Price in EUR (Netto) */
  price: number;
  /** Detailed description */
  details: {
    fokuspunkte: string[];
    inhalt: string[];
    phasenziel: string;
    output: string[];
  };
}

export interface ProposalSummary {
  /** Net total */
  netTotal: number;
  /** VAT rate (0, 0.20, or 0.22) */
  vatRate: number;
  /** VAT amount */
  vatAmount: number;
  /** Gross total */
  grossTotal: number;
  /** Discount applied (if any) */
  discount?: {
    rate: number;
    amount: number;
    reason: string;
  };
}

export interface PaymentInstallment {
  percentage: number;
  amount: number;
  label: string;
}

export interface Proposal {
  /** Unique proposal ID */
  id: string;

  /** Creation date (ISO string) */
  createdAt: string;

  /** Language of the proposal */
  language: Language;

  /** ClickUp Task ID */
  clickupTaskId: string;

  /** Google Doc ID (set after creation) */
  googleDocId?: string;

  /** Google Doc URL (set after creation) */
  googleDocUrl?: string;

  /** Section 1: Cover Letter */
  coverLetter: {
    greeting: string;
    body: string;
    teamParagraph: string;
    closing: string;
  };

  /** Section 2: Legal Notice */
  legalNotice: {
    validity: string;
    copyright: string;
    costOverrun: string;
    agb: string;
  };

  /** Section 3: Calculation */
  calculation: {
    rows: ProposalCalculationRow[];
    projectPhases: ProjectPhase[];
  };

  /** Section 4: Summary & Terms */
  summary: {
    financials: ProposalSummary;
    paymentTerms: PaymentInstallment[];
    inclusions: string[];
    exclusions: string[];
    signatureSection: {
      agreementText: string;
      agencyName: string;
      partnerName: string;
    };
  };

  /** Section 5: References */
  references: {
    entries: ReferenceEntry[];
    portfolioLink: string;
  };

  /** Metadata */
  metadata: {
    kundenName: string;
    ansprechpartner: string;
    services: string[];
    branche: string;
    isRetainer: boolean;
    generatedBy: string;
  };
}

export interface ReferenceEntry {
  partnerName: string;
  industry: string;
  description: string;
  testimonial?: string;
}

/**
 * Generate a document title from proposal data
 */
export function generateDocTitle(kundenName: string): string {
  const date = new Date().toISOString().split('T')[0];
  return `Angebot_${kundenName.replace(/\s+/g, '_')}_${date}`;
}

/**
 * Create an empty proposal scaffold
 */
export function createEmptyProposal(taskId: string, language: Language): Proposal {
  return {
    id: `proposal_${taskId}_${Date.now()}`,
    createdAt: new Date().toISOString(),
    language,
    clickupTaskId: taskId,
    coverLetter: { greeting: '', body: '', teamParagraph: '', closing: '' },
    legalNotice: { validity: '', copyright: '', costOverrun: '', agb: '' },
    calculation: { rows: [], projectPhases: [] },
    summary: {
      financials: { netTotal: 0, vatRate: 0, vatAmount: 0, grossTotal: 0 },
      paymentTerms: [],
      inclusions: [],
      exclusions: [],
      signatureSection: { agreementText: '', agencyName: 'zukunvt GmbH', partnerName: '' },
    },
    references: { entries: [], portfolioLink: 'https://partner.zukunvt.it' },
    metadata: {
      kundenName: '',
      ansprechpartner: '',
      services: [],
      branche: '',
      isRetainer: false,
      generatedBy: 'zukunvt-angebot-automation',
    },
  };
}
