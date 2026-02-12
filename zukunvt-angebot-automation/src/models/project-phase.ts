/**
 * Project Phase Model
 * Defines phases for proposal calculation section
 */

export interface PhaseDeliverable {
  title: string;
  description: string;
}

export interface ProjectPhase {
  /** Phase number (1-based) */
  phaseNumber: number;

  /** Phase title */
  title: string;

  /** Time range (e.g., "Woche 1-2") */
  timeRange: string;

  /** Focus areas */
  fokuspunkte: string[];

  /** Activities / contents (workshops, meetings, deliverables) */
  inhalt: string[];

  /** Phase objective */
  phasenziel: string;

  /** Concrete deliverables / outputs */
  output: string[];

  /** Price for this phase (EUR, Netto) */
  price: number;
}

export interface ProjectPlan {
  /** All phases of the project */
  phases: ProjectPhase[];

  /** Total project duration description */
  totalDuration: string;

  /** Whether this is a retainer setup */
  isRetainer: boolean;

  /** Total price (sum of all phases, EUR, Netto) */
  totalPrice: number;
}

/**
 * Template phases for standard services — used as a basis for AI generation
 */
export const PHASE_TEMPLATES: Record<string, ProjectPhase[]> = {
  'Strategy Foundation': [
    {
      phaseNumber: 1,
      title: 'Discovery & Analyse',
      timeRange: 'Woche 1-2',
      fokuspunkte: ['Ist-Analyse', 'Markt & Wettbewerb', 'Stakeholder-Interviews'],
      inhalt: ['Kick-off Workshop (2h)', '3-5 Stakeholder-Interviews', 'Desk Research'],
      phasenziel: 'Umfassendes Verständnis der Ausgangslage',
      output: ['Analyse-Dokument', 'Wettbewerbsmatrix'],
      price: 0,
    },
    {
      phaseNumber: 2,
      title: 'Strategieentwicklung',
      timeRange: 'Woche 3-4',
      fokuspunkte: ['Positionierung', 'Wertangebot', 'USP'],
      inhalt: ['Strategy Workshop (4h)', 'Business Model Canvas'],
      phasenziel: 'Klare strategische Positionierung',
      output: ['Positionierungspapier', 'BMC', 'OKR-Framework'],
      price: 0,
    },
    {
      phaseNumber: 3,
      title: 'Kommunikationsplanung',
      timeRange: 'Woche 5-6',
      fokuspunkte: ['Zielgruppen', 'Kanäle', 'Botschaften'],
      inhalt: ['Kommunikationsworkshop (3h)'],
      phasenziel: 'Konkreter Umsetzungsplan',
      output: ['Kommunikationsplan', 'Content-Strategie'],
      price: 0,
    },
    {
      phaseNumber: 4,
      title: 'Präsentation & Übergabe',
      timeRange: 'Woche 7-8',
      fokuspunkte: ['Ergebnispräsentation', 'Handlungsempfehlungen'],
      inhalt: ['Abschlusspräsentation', 'Handover-Meeting'],
      phasenziel: 'Handlungsfähigkeit des Partners',
      output: ['Strategie-Deck', 'Umsetzungs-Roadmap'],
      price: 0,
    },
  ],

  'Brand Transformation': [
    {
      phaseNumber: 1,
      title: 'Brand Audit',
      timeRange: 'Woche 1-3',
      fokuspunkte: ['Markenanalyse', 'Wettbewerbslandschaft', 'Zielgruppen-Insights'],
      inhalt: ['Brand Audit Workshop (3h)', 'Stakeholder-Interviews', 'Marktanalyse'],
      phasenziel: 'Ganzheitliches Verständnis der aktuellen Markenposition',
      output: ['Brand Audit Report', 'Competitive Analysis'],
      price: 0,
    },
    {
      phaseNumber: 2,
      title: 'Brand Strategy',
      timeRange: 'Woche 4-6',
      fokuspunkte: ['Brand Architecture', 'Positionierung', 'Tone of Voice'],
      inhalt: ['Strategy Workshop (4h)', 'Brand Positioning Session'],
      phasenziel: 'Strategische Markengrundlage',
      output: ['Brand Strategy Document', 'Tone of Voice Guidelines', 'Kommunikationsplan'],
      price: 0,
    },
    {
      phaseNumber: 3,
      title: 'Brand Design',
      timeRange: 'Woche 7-9',
      fokuspunkte: ['Visual Identity', 'Design System', 'Key Visuals'],
      inhalt: ['Design Konzept-Präsentation', '2 Korrekturschleifen'],
      phasenziel: 'Visuell differenzierende Markenidentität',
      output: ['Logo & Visual Identity', 'Brand Guidelines', 'Design Templates'],
      price: 0,
    },
    {
      phaseNumber: 4,
      title: 'Brand Implementation',
      timeRange: 'Woche 10-12',
      fokuspunkte: ['Rollout-Planung', 'Asset-Produktion', 'Team-Training'],
      inhalt: ['Implementation Workshop', 'Asset Handover'],
      phasenziel: 'Marktreife Markenimplementierung',
      output: ['Brand Assets Package', 'Implementation Roadmap', 'Brand Training Deck'],
      price: 0,
    },
  ],

  'Retainer': [
    {
      phaseNumber: 1,
      title: 'Setup & Onboarding',
      timeRange: 'Woche 1-2',
      fokuspunkte: ['Kick-off', 'Tool-Setup', 'Asset-Übergabe', 'Team-Vorstellung'],
      inhalt: ['Kick-off Workshop (2h)', 'Tool-Onboarding', 'Prozess-Definition'],
      phasenziel: 'Reibungsloser Projektstart',
      output: ['Onboarding-Dokument', 'Prozess-Handbuch', 'Reporting-Template'],
      price: 0,
    },
    {
      phaseNumber: 2,
      title: 'Anlaufphase',
      timeRange: 'Woche 3-4',
      fokuspunkte: ['Erste Deliverables', 'Prozess-Feintuning', 'Reporting-Setup'],
      inhalt: ['Wöchentliche Abstimmung', 'Erste Content-Produktion'],
      phasenziel: 'Eingespieltes Team und Prozesse',
      output: ['Erste Deliverables', 'Prozess-Dokumentation'],
      price: 0,
    },
    {
      phaseNumber: 3,
      title: 'Regelbetrieb',
      timeRange: 'Ab Monat 2',
      fokuspunkte: ['Kontinuierliche Lieferung', 'Performance Monitoring', 'Optimierung'],
      inhalt: ['Wöchentliche/Monatliche Meetings', 'Laufende Produktion', 'Monatliches Reporting'],
      phasenziel: 'Nachhaltige Ergebnisse und kontinuierliche Optimierung',
      output: ['Monatliche Deliverables', 'Performance Reports', 'Optimierungsvorschläge'],
      price: 0,
    },
  ],
};

/**
 * Calculate total price across all phases
 */
export function calculateTotalPrice(phases: ProjectPhase[]): number {
  return phases.reduce((sum, phase) => sum + phase.price, 0);
}
