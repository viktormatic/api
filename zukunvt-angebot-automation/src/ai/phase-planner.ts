/**
 * Phase Planner
 * Generates project phases based on selected services, budget, and timeline
 */

import { ServiceType } from '../config/team';
import { PRICING_2026 } from '../config/pricing';
import { ProjectPhase, ProjectPlan, PHASE_TEMPLATES } from '../models/project-phase';
import { BudgetRange, Timeline, parseBudgetRange, parseTimelineMonths } from '../models/client-data';

interface PhasePlannerInput {
  services: ServiceType[];
  budget: BudgetRange;
  timeline: Timeline;
  isRetainer: boolean;
}

/**
 * Generate a project plan with phases based on selected services
 */
export function generateProjectPlan(input: PhasePlannerInput): ProjectPlan {
  const { services, budget, timeline, isRetainer } = input;
  const budgetRange = parseBudgetRange(budget);
  const timelineRange = parseTimelineMonths(timeline);

  if (isRetainer || timeline === 'Retainer') {
    return generateRetainerPlan(services, budgetRange);
  }

  return generateProjectPhases(services, budgetRange, timelineRange);
}

/**
 * Generate phases for a project-based engagement
 */
function generateProjectPhases(
  services: ServiceType[],
  budgetRange: { min: number; max: number },
  timelineRange: { min: number; max: number }
): ProjectPlan {
  const allPhases: ProjectPhase[] = [];
  let phaseCounter = 0;

  // Combine phases from all selected services
  for (const service of services) {
    const templatePhases = getTemplatePhases(service);
    const serviceBudget = budgetRange.max === Infinity
      ? budgetRange.min
      : Math.round((budgetRange.min + budgetRange.max) / 2);
    const budgetPerService = Math.round(serviceBudget / services.length);

    for (const templatePhase of templatePhases) {
      phaseCounter++;
      const phasePrice = Math.round(budgetPerService / templatePhases.length);

      allPhases.push({
        ...templatePhase,
        phaseNumber: phaseCounter,
        price: phasePrice,
      });
    }
  }

  const totalPrice = allPhases.reduce((sum, p) => sum + p.price, 0);
  const totalWeeks = timelineRange.max * 4;
  const totalDuration = `${timelineRange.min}-${timelineRange.max} Monate (${totalWeeks} Wochen)`;

  return {
    phases: allPhases,
    totalDuration,
    isRetainer: false,
    totalPrice,
  };
}

/**
 * Generate phases for a retainer engagement
 */
function generateRetainerPlan(
  services: ServiceType[],
  budgetRange: { min: number; max: number }
): ProjectPlan {
  const retainerPhases = PHASE_TEMPLATES['Retainer'] ?? [];
  const monthlyRate = getRetainerRate(services);

  const phases: ProjectPhase[] = retainerPhases.map((phase, index) => ({
    ...phase,
    phaseNumber: index + 1,
    price: index === 0 ? 0 : monthlyRate, // Setup phase is included
  }));

  return {
    phases,
    totalDuration: 'Laufender Retainer (monatlich)',
    isRetainer: true,
    totalPrice: monthlyRate,
  };
}

/**
 * Get template phases for a service type
 */
function getTemplatePhases(service: ServiceType): ProjectPhase[] {
  // Direct template match
  if (PHASE_TEMPLATES[service]) {
    return PHASE_TEMPLATES[service];
  }

  // Map services to closest template
  switch (service) {
    case 'Strategy Foundation':
      return PHASE_TEMPLATES['Strategy Foundation'];
    case 'Brand Transformation':
      return PHASE_TEMPLATES['Brand Transformation'];
    case 'Agile Activation':
      return generateAgileActivationPhases();
    case 'Content Engine':
    case 'Digital Growth':
    case 'Full-Service Partner':
    case 'Employer Branding':
      return PHASE_TEMPLATES['Retainer'] ?? generateGenericPhases(service);
    case 'AI Audit':
      return generateAIAuditPhases();
    case 'AI Setup':
      return generateAISetupPhases();
    case 'Custom':
      return generateGenericPhases(service);
    default:
      return generateGenericPhases(service);
  }
}

/**
 * Determine monthly retainer rate based on services
 */
function getRetainerRate(services: ServiceType[]): number {
  const retainerMap: Partial<Record<ServiceType, number>> = {
    'Strategy Foundation': PRICING_2026.retainer.strategySparring,
    'Brand Transformation': PRICING_2026.retainer.brandGuardian,
    'Content Engine': PRICING_2026.retainer.contentEngine,
    'Digital Growth': PRICING_2026.retainer.digitalGrowth,
    'Full-Service Partner': PRICING_2026.retainer.fullServicePartner,
    'Employer Branding': PRICING_2026.retainer.employerBranding,
    'AI Audit': PRICING_2026.aiServices.aiRetainer,
    'AI Setup': PRICING_2026.aiServices.aiRetainer,
  };

  // For Full-Service, use the full-service rate
  if (services.includes('Full-Service Partner')) {
    return PRICING_2026.retainer.fullServicePartner;
  }

  // Sum individual retainer rates
  let total = 0;
  for (const service of services) {
    total += retainerMap[service] ?? PRICING_2026.retainer.strategySparring;
  }

  return total;
}

function generateAgileActivationPhases(): ProjectPhase[] {
  return [
    {
      phaseNumber: 1,
      title: 'Customer Journey Mapping',
      timeRange: 'Woche 1-2',
      fokuspunkte: ['Touchpoint-Analyse', 'Lead-Funnel Definition', 'Zielgruppen-Segmentierung'],
      inhalt: ['Journey Mapping Workshop (3h)', 'Funnel-Analyse'],
      phasenziel: 'Klare Customer Journey mit definierten Touchpoints',
      output: ['Customer Journey Map', 'Lead-Funnel-Dokument'],
      price: 0,
    },
    {
      phaseNumber: 2,
      title: 'Content & Channel Strategy',
      timeRange: 'Woche 3-4',
      fokuspunkte: ['Content-Planung', 'Kanal-Strategie', 'KPI-Definition'],
      inhalt: ['Content Strategy Workshop (3h)', 'Channel Audit'],
      phasenziel: 'Umsetzungsbereiter Content- und Kanalplan',
      output: ['Content Calendar (3 Monate)', 'Channel Strategy', 'KPI-Dashboard-Setup'],
      price: 0,
    },
    {
      phaseNumber: 3,
      title: 'Activation Sprint',
      timeRange: 'Woche 5-8',
      fokuspunkte: ['Campaign Launch', 'Lead Generation', 'Performance Tracking'],
      inhalt: ['Sprint Planning', 'Wöchentliche Stand-ups', 'Campaign Management'],
      phasenziel: 'Erste messbare Ergebnisse und optimierte Prozesse',
      output: ['Campaign Assets', 'Performance Report', 'Optimierungsempfehlungen'],
      price: 0,
    },
  ];
}

function generateAIAuditPhases(): ProjectPhase[] {
  return [
    {
      phaseNumber: 1,
      title: 'AI-Readiness Assessment',
      timeRange: 'Woche 1',
      fokuspunkte: ['Prozess-Analyse', 'Tool-Landschaft', 'Team-Kompetenz'],
      inhalt: ['Kick-off Workshop (2h)', 'Stakeholder-Interviews (3-5)'],
      phasenziel: 'Verständnis der aktuellen AI-Reife',
      output: ['AI-Readiness Scorecard'],
      price: 0,
    },
    {
      phaseNumber: 2,
      title: 'Potenzialanalyse & Empfehlungen',
      timeRange: 'Woche 2-3',
      fokuspunkte: ['Use-Case Identifikation', 'ROI-Schätzung', 'Priorisierung'],
      inhalt: ['Analyse-Phase', 'Benchmark-Vergleich'],
      phasenziel: 'Priorisierte AI-Roadmap',
      output: ['AI Audit Report', 'Use-Case Matrix', 'Implementierungs-Roadmap'],
      price: 0,
    },
    {
      phaseNumber: 3,
      title: 'Präsentation & Quick Wins',
      timeRange: 'Woche 4',
      fokuspunkte: ['Ergebnispräsentation', 'Quick-Win Implementation'],
      inhalt: ['Abschlusspräsentation (2h)', 'Quick-Win Workshop'],
      phasenziel: 'Handlungsfähigkeit und erste Quick Wins',
      output: ['Präsentations-Deck', 'Quick-Win Implementierungsplan'],
      price: 0,
    },
  ];
}

function generateAISetupPhases(): ProjectPhase[] {
  return [
    {
      phaseNumber: 1,
      title: 'Anforderungsanalyse & Tool-Auswahl',
      timeRange: 'Woche 1-2',
      fokuspunkte: ['Anforderungen', 'Tool-Evaluation', 'Architektur-Planung'],
      inhalt: ['Requirements Workshop (3h)', 'Tool-Demos'],
      phasenziel: 'Klare Tool-Entscheidung und Implementierungsplan',
      output: ['Requirements Document', 'Tool-Evaluation Matrix'],
      price: 0,
    },
    {
      phaseNumber: 2,
      title: 'Implementation & Integration',
      timeRange: 'Woche 3-6',
      fokuspunkte: ['Tool-Setup', 'Workflow-Integration', 'Daten-Migration'],
      inhalt: ['Technische Implementation', 'Integration-Tests'],
      phasenziel: 'Funktionsfähige AI-Tool-Infrastruktur',
      output: ['Konfigurierte Tools', 'Integrations-Dokumentation'],
      price: 0,
    },
    {
      phaseNumber: 3,
      title: 'Training & Übergabe',
      timeRange: 'Woche 7-8',
      fokuspunkte: ['Team-Training', 'Dokumentation', 'Support-Setup'],
      inhalt: ['Team Training Sessions (2x3h)', 'Hands-on Workshops'],
      phasenziel: 'Eigenständige Nutzung durch das Team',
      output: ['Training-Materialien', 'Benutzerhandbuch', 'Support-Prozess'],
      price: 0,
    },
  ];
}

function generateGenericPhases(service: ServiceType): ProjectPhase[] {
  return [
    {
      phaseNumber: 1,
      title: 'Discovery & Planung',
      timeRange: 'Woche 1-2',
      fokuspunkte: ['Bestandsaufnahme', 'Zielsetzung', 'Projektplanung'],
      inhalt: ['Kick-off Workshop (2h)', 'Stakeholder-Interviews'],
      phasenziel: 'Klare Projekt-Roadmap',
      output: ['Projekt-Brief', 'Meilensteinplan'],
      price: 0,
    },
    {
      phaseNumber: 2,
      title: 'Konzeption & Entwicklung',
      timeRange: 'Woche 3-6',
      fokuspunkte: ['Konzeptentwicklung', 'Umsetzung', 'Qualitätssicherung'],
      inhalt: ['Regelmäßige Abstimmungen', 'Iterative Entwicklung'],
      phasenziel: 'Fertige Lösung zur Review',
      output: ['Konzeptdokument', 'Deliverables'],
      price: 0,
    },
    {
      phaseNumber: 3,
      title: 'Finalisierung & Übergabe',
      timeRange: 'Woche 7-8',
      fokuspunkte: ['Finalisierung', 'Handover', 'Dokumentation'],
      inhalt: ['Abschlusspräsentation', 'Übergabe-Meeting'],
      phasenziel: 'Erfolgreich abgeschlossenes Projekt',
      output: ['Finale Deliverables', 'Dokumentation', 'Handover-Paket'],
      price: 0,
    },
  ];
}
