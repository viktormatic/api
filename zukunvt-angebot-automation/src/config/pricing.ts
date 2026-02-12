/**
 * zukunvt 2026 Preisliste
 * All prices in EUR, Netto (excluding VAT)
 */

export const PRICING_2026 = {
  /** Stundensätze (Netto, EUR/h) */
  hourlyRates: {
    strategicConsulting: 150,
    digitalGrowthAI: 130,
    creativeDesign: 105,
    projectManagement: 105,
    copywritingEditing: 105,
  },

  /** Produktionskosten */
  production: {
    /** pro 1.000 Zeichen */
    proofreading: 8.5,
    /** pro Standardzeile (DE/IT/EN) */
    translation: 2.6,
    /** pro km */
    travel: 0.85,
    /** auf externe Kosten */
    handlingCommissionMin: 0.05,
    handlingCommissionMax: 0.15,
  },

  /** Productized Services — Retainer, monatlich (EUR) */
  retainer: {
    strategySparring: 1800,
    brandGuardian: 2500,
    employerBranding: 3500,
    contentEngine: 4500,
    eventActivation: 5000,
    digitalGrowth: 6000,
    fullServicePartner: 12000,
  },

  /** AI Services (EUR) */
  aiServices: {
    /** einmalig */
    aiAudit: 3500,
    /** einmalig, Spanne */
    aiSetup: { min: 8000, max: 15000 },
    /** monatlich */
    aiRetainer: 1500,
  },

  /** Rabatte nach Retainer-Laufzeit */
  discounts: {
    months6: 0,
    months12: 0.05,
    months24: 0.1,
  },

  /** MwSt-Sätze nach Land */
  vat: {
    italy: 0.22,
    austria: 0.2,
    euReverseCharge: 0,
  },
} as const;

export type HourlyRateCategory = keyof typeof PRICING_2026.hourlyRates;
export type RetainerService = keyof typeof PRICING_2026.retainer;
export type VatRegion = keyof typeof PRICING_2026.vat;

/**
 * Zahlungsbedingungen nach Projektgröße
 */
export const PAYMENT_TERMS = {
  small: {
    label: '€5K–€20K',
    minAmount: 5000,
    maxAmount: 20000,
    installments: [
      { percentage: 50, label: 'Vorauszahlung bei Auftragserteilung' },
      { percentage: 50, label: 'Bei Projektabschluss' },
    ],
  },
  large: {
    label: '>€20K',
    minAmount: 20001,
    maxAmount: Infinity,
    installments: [
      { percentage: 30, label: 'Vorauszahlung bei Auftragserteilung' },
      { percentage: 40, label: 'Bei Projektmitte / Milestone' },
      { percentage: 30, label: 'Bei Projektabschluss' },
    ],
  },
  retainer: {
    label: 'Retainer',
    minAmount: 0,
    maxAmount: Infinity,
    installments: [
      { percentage: 100, label: 'Monatlich, Rechnung zu Monatsbeginn' },
    ],
  },
} as const;

/**
 * Calculate VAT for a given region
 */
export function calculateVat(netAmount: number, region: VatRegion): number {
  return netAmount * PRICING_2026.vat[region];
}

/**
 * Calculate retainer discount based on contract duration
 */
export function calculateRetainerDiscount(
  monthlyRate: number,
  durationMonths: number
): { discountRate: number; discountedRate: number } {
  let discountRate = 0;
  if (durationMonths >= 24) {
    discountRate = PRICING_2026.discounts.months24;
  } else if (durationMonths >= 12) {
    discountRate = PRICING_2026.discounts.months12;
  }
  return {
    discountRate,
    discountedRate: monthlyRate * (1 - discountRate),
  };
}

/**
 * Determine payment terms based on total project value
 */
export function getPaymentTerms(totalAmount: number, isRetainer: boolean) {
  if (isRetainer) return PAYMENT_TERMS.retainer;
  if (totalAmount <= 20000) return PAYMENT_TERMS.small;
  return PAYMENT_TERMS.large;
}
