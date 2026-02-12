/**
 * Client data model — maps ClickUp Custom Fields to typed data
 */

import { ServiceType } from '../config/team';

export type Language = 'DE' | 'IT' | 'EN';

export type BudgetRange = '<5k' | '5-10k' | '10-20k' | '20-50k' | '>50k';

export type Timeline = '1-3 Monate' | '3-6 Monate' | '6-12 Monate' | 'Retainer';

export type Industry =
  | 'Public Sector'
  | 'Tourism'
  | 'B2B'
  | 'Technology'
  | 'Retail'
  | 'Healthcare'
  | 'Education'
  | 'Professional Services'
  | 'Other';

export interface AngebotTaskData {
  /** ClickUp Task ID */
  taskId: string;

  /** Firmenname / Projektname (= ClickUp Task Name) */
  taskName: string;

  /** Kundenname (Firma) */
  kundenName: string;

  /** Kontaktperson */
  ansprechpartner: string;

  /** E-Mail Ansprechpartner */
  email: string;

  /** Selected services */
  services: ServiceType[];

  /** Industry / Branche */
  branche: Industry;

  /** Freitext: Was braucht der Kunde? */
  projektBeschreibung: string;

  /** Budget range */
  budget: BudgetRange;

  /** Project timeline */
  timeline: Timeline;

  /** Angebotssprache */
  sprache: Language;

  /** Bestandskunde ja/nein */
  bestehenderKunde: boolean;

  /** Interne Notizen zum Angebot */
  notizen: string;
}

/**
 * Parse budget range string to numeric min/max
 */
export function parseBudgetRange(budget: BudgetRange): { min: number; max: number } {
  switch (budget) {
    case '<5k':
      return { min: 0, max: 5000 };
    case '5-10k':
      return { min: 5000, max: 10000 };
    case '10-20k':
      return { min: 10000, max: 20000 };
    case '20-50k':
      return { min: 20000, max: 50000 };
    case '>50k':
      return { min: 50000, max: Infinity };
  }
}

/**
 * Parse timeline to approximate months
 */
export function parseTimelineMonths(timeline: Timeline): { min: number; max: number } {
  switch (timeline) {
    case '1-3 Monate':
      return { min: 1, max: 3 };
    case '3-6 Monate':
      return { min: 3, max: 6 };
    case '6-12 Monate':
      return { min: 6, max: 12 };
    case 'Retainer':
      return { min: 6, max: 24 };
  }
}

/**
 * Validate required fields for proposal generation
 */
export function validateTaskData(data: Partial<AngebotTaskData>): {
  valid: boolean;
  missingFields: string[];
} {
  const requiredFields: (keyof AngebotTaskData)[] = [
    'taskId',
    'taskName',
    'kundenName',
    'ansprechpartner',
    'email',
    'services',
    'branche',
    'projektBeschreibung',
    'budget',
    'timeline',
    'sprache',
  ];

  const missingFields = requiredFields.filter(
    (field) => data[field] === undefined || data[field] === null || data[field] === ''
  );

  // Services must be a non-empty array
  if (Array.isArray(data.services) && data.services.length === 0) {
    missingFields.push('services');
  }

  return {
    valid: missingFields.length === 0,
    missingFields,
  };
}
