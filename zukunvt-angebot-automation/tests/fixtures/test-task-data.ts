/**
 * Test fixtures — sample task data for testing proposal generation
 */

import { AngebotTaskData } from '../../src/models/client-data';

export const STRATEGY_B2B_TASK: AngebotTaskData = {
  taskId: 'test-001',
  taskName: 'TechCorp Strategy Foundation',
  kundenName: 'TechCorp GmbH',
  ansprechpartner: 'Dr. Anna Müller',
  email: 'anna.mueller@techcorp.de',
  services: ['Strategy Foundation'],
  branche: 'Technology',
  projektBeschreibung:
    'TechCorp sucht eine strategische Neupositionierung. Das Unternehmen hat 150 Mitarbeiter und möchte sich als Marktführer im DACH-Raum positionieren. Fokus auf digitale Transformation und Innovation.',
  budget: '10-20k',
  timeline: '3-6 Monate',
  sprache: 'DE',
  bestehenderKunde: false,
  notizen: 'Sitz in Wien, Österreich. Erster Kontakt über LinkedIn.',
};

export const FULLSERVICE_RETAINER_TASK: AngebotTaskData = {
  taskId: 'test-002',
  taskName: 'Alpina Tourism Full-Service',
  kundenName: 'Alpina Tourism AG',
  ansprechpartner: 'Markus Hofer',
  email: 'hofer@alpina-tourism.it',
  services: ['Full-Service Partner'],
  branche: 'Tourism',
  projektBeschreibung:
    'Alpina Tourism sucht einen Full-Service Partner für Destination Marketing. Bestehende Marke soll neu belebt werden, digitale Kanäle ausgebaut und Content-Produktion professionalisiert.',
  budget: '>50k',
  timeline: 'Retainer',
  sprache: 'DE',
  bestehenderKunde: false,
  notizen: 'Sitz in Südtirol, Italien. Sehr großes Potenzial.',
};

export const BRAND_MARKETING_KOMBI_TASK: AngebotTaskData = {
  taskId: 'test-003',
  taskName: 'Comune di Bolzano Brand + Marketing',
  kundenName: 'Comune di Bolzano',
  ansprechpartner: 'Dott. Marco Rossi',
  email: 'marco.rossi@comune.bolzano.it',
  services: ['Brand Transformation', 'Content Engine'],
  branche: 'Public Sector',
  projektBeschreibung:
    'La città di Bolzano cerca un partner per rinnovare il brand istituzionale e attivare una strategia di content marketing per la comunicazione con i cittadini.',
  budget: '20-50k',
  timeline: '6-12 Monate',
  sprache: 'IT',
  bestehenderKunde: false,
  notizen: 'Öffentlicher Auftraggeber, Italien. Ausschreibungsverfahren.',
};

export const AI_AUDIT_BESTANDSKUNDE_TASK: AngebotTaskData = {
  taskId: 'test-004',
  taskName: 'LegalPartners AI Audit',
  kundenName: 'LegalPartners KG',
  ansprechpartner: 'Mag. Sarah Berger',
  email: 'berger@legalpartners.at',
  services: ['AI Audit'],
  branche: 'Professional Services',
  projektBeschreibung:
    'Bestandskunde LegalPartners möchte einen AI-Readiness Check. Die Kanzlei will AI-Tools in Dokumentenmanagement und Recherche integrieren.',
  budget: '<5k',
  timeline: '1-3 Monate',
  sprache: 'DE',
  bestehenderKunde: true,
  notizen: 'Wien, Österreich. Bestehende Zusammenarbeit seit 2024 (Brand Refresh).',
};

export const ALL_TEST_TASKS: AngebotTaskData[] = [
  STRATEGY_B2B_TASK,
  FULLSERVICE_RETAINER_TASK,
  BRAND_MARKETING_KOMBI_TASK,
  AI_AUDIT_BESTANDSKUNDE_TASK,
];

/**
 * Sample ClickUp custom fields array (as returned by API)
 */
export const SAMPLE_CLICKUP_CUSTOM_FIELDS = [
  {
    id: 'field-001',
    name: 'Kundenname',
    type: 'text',
    value: 'TechCorp GmbH',
  },
  {
    id: 'field-002',
    name: 'Ansprechpartner',
    type: 'text',
    value: 'Dr. Anna Müller',
  },
  {
    id: 'field-003',
    name: 'E-Mail',
    type: 'email',
    value: 'anna.mueller@techcorp.de',
  },
  {
    id: 'field-004',
    name: 'Services',
    type: 'labels',
    value: [{ label: 'Strategy Foundation' }],
    type_config: {
      options: [
        { id: 'opt-1', name: 'Strategy Foundation', label: 'Strategy Foundation' },
        { id: 'opt-2', name: 'Brand Transformation', label: 'Brand Transformation' },
        { id: 'opt-3', name: 'Content Engine', label: 'Content Engine' },
      ],
    },
  },
  {
    id: 'field-005',
    name: 'Branche',
    type: 'drop_down',
    value: 'Technology',
  },
  {
    id: 'field-006',
    name: 'Projektbeschreibung',
    type: 'text',
    value: 'Strategische Neupositionierung im DACH-Raum.',
  },
  {
    id: 'field-007',
    name: 'Budget',
    type: 'drop_down',
    value: '10-20k',
  },
  {
    id: 'field-008',
    name: 'Timeline',
    type: 'drop_down',
    value: '3-6 Monate',
  },
  {
    id: 'field-009',
    name: 'Sprache',
    type: 'drop_down',
    value: 'DE',
  },
  {
    id: 'field-010',
    name: 'Bestandskunde',
    type: 'checkbox',
    value: false,
  },
  {
    id: 'field-011',
    name: 'Notizen',
    type: 'text',
    value: 'Sitz in Wien, Österreich.',
  },
  {
    id: 'field-012',
    name: 'Angebot Link',
    type: 'url',
    value: null,
  },
];
