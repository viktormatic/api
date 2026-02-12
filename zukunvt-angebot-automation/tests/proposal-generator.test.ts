/**
 * Tests for the proposal generation pipeline
 */

import { parseTaskData } from '../src/clickup/custom-fields';
import { validateTaskData, parseBudgetRange, parseTimelineMonths } from '../src/models/client-data';
import { generateProjectPlan } from '../src/ai/phase-planner';
import { calculateVat, getPaymentTerms, calculateRetainerDiscount } from '../src/config/pricing';
import { getTeamForServices, generateTeamParagraph } from '../src/config/team';
import { generateDocTitle, createEmptyProposal } from '../src/models/proposal';
import { parseProposalText, extractPricingFromTemplate } from '../src/google/template-parser';
import {
  STRATEGY_B2B_TASK,
  FULLSERVICE_RETAINER_TASK,
  BRAND_MARKETING_KOMBI_TASK,
  AI_AUDIT_BESTANDSKUNDE_TASK,
  SAMPLE_CLICKUP_CUSTOM_FIELDS,
} from './fixtures/test-task-data';

describe('ClickUp Custom Fields Parser', () => {
  it('should parse custom fields into AngebotTaskData', () => {
    const result = parseTaskData('task-123', 'Test Task', SAMPLE_CLICKUP_CUSTOM_FIELDS);

    expect(result.taskId).toBe('task-123');
    expect(result.kundenName).toBe('TechCorp GmbH');
    expect(result.ansprechpartner).toBe('Dr. Anna Müller');
    expect(result.email).toBe('anna.mueller@techcorp.de');
    expect(result.services).toEqual(['Strategy Foundation']);
    expect(result.branche).toBe('Technology');
    expect(result.budget).toBe('10-20k');
    expect(result.timeline).toBe('3-6 Monate');
    expect(result.sprache).toBe('DE');
    expect(result.bestehenderKunde).toBe(false);
  });

  it('should handle missing fields gracefully', () => {
    const result = parseTaskData('task-empty', 'Empty Task', []);

    expect(result.taskId).toBe('task-empty');
    expect(result.kundenName).toBe('Empty Task'); // Falls back to task name
    expect(result.ansprechpartner).toBe('');
    expect(result.services).toEqual([]);
    expect(result.sprache).toBe('DE'); // Default
  });
});

describe('Task Data Validation', () => {
  it('should validate a complete task', () => {
    const result = validateTaskData(STRATEGY_B2B_TASK);
    expect(result.valid).toBe(true);
    expect(result.missingFields).toEqual([]);
  });

  it('should detect missing required fields', () => {
    const result = validateTaskData({
      taskId: 'test',
      taskName: 'Test',
    });
    expect(result.valid).toBe(false);
    expect(result.missingFields).toContain('kundenName');
    expect(result.missingFields).toContain('email');
    expect(result.missingFields).toContain('services');
  });

  it('should reject empty services array', () => {
    const result = validateTaskData({
      ...STRATEGY_B2B_TASK,
      services: [],
    });
    expect(result.valid).toBe(false);
    expect(result.missingFields).toContain('services');
  });
});

describe('Budget & Timeline Parsing', () => {
  it('should parse budget ranges correctly', () => {
    expect(parseBudgetRange('<5k')).toEqual({ min: 0, max: 5000 });
    expect(parseBudgetRange('10-20k')).toEqual({ min: 10000, max: 20000 });
    expect(parseBudgetRange('>50k')).toEqual({ min: 50000, max: Infinity });
  });

  it('should parse timeline ranges correctly', () => {
    expect(parseTimelineMonths('1-3 Monate')).toEqual({ min: 1, max: 3 });
    expect(parseTimelineMonths('Retainer')).toEqual({ min: 6, max: 24 });
  });
});

describe('Pricing Calculations', () => {
  it('should calculate Italian VAT correctly', () => {
    expect(calculateVat(10000, 'italy')).toBe(2200);
  });

  it('should calculate Austrian VAT correctly', () => {
    expect(calculateVat(10000, 'austria')).toBe(2000);
  });

  it('should return 0 for EU Reverse Charge', () => {
    expect(calculateVat(10000, 'euReverseCharge')).toBe(0);
  });

  it('should return correct payment terms for small projects', () => {
    const terms = getPaymentTerms(15000, false);
    expect(terms.installments).toHaveLength(2);
    expect(terms.installments[0].percentage).toBe(50);
  });

  it('should return correct payment terms for large projects', () => {
    const terms = getPaymentTerms(30000, false);
    expect(terms.installments).toHaveLength(3);
    expect(terms.installments[0].percentage).toBe(30);
  });

  it('should return retainer payment terms', () => {
    const terms = getPaymentTerms(12000, true);
    expect(terms.installments).toHaveLength(1);
    expect(terms.installments[0].percentage).toBe(100);
  });

  it('should calculate retainer discounts', () => {
    const result12 = calculateRetainerDiscount(4500, 12);
    expect(result12.discountRate).toBe(0.05);
    expect(result12.discountedRate).toBe(4275);

    const result24 = calculateRetainerDiscount(4500, 24);
    expect(result24.discountRate).toBe(0.10);
    expect(result24.discountedRate).toBe(4050);

    const result6 = calculateRetainerDiscount(4500, 6);
    expect(result6.discountRate).toBe(0);
    expect(result6.discountedRate).toBe(4500);
  });
});

describe('Team Assignments', () => {
  it('should assign strategy and PM teams for Strategy Foundation', () => {
    const teams = getTeamForServices(['Strategy Foundation']);
    const departmentDescriptions = teams.map((t) => t.description);
    expect(departmentDescriptions).toContain('Strategische Führung und Business Consulting');
    expect(departmentDescriptions).toContain('Persönliche Betreuung und Projektkoordination');
  });

  it('should assign all teams for Full-Service Partner', () => {
    const teams = getTeamForServices(['Full-Service Partner']);
    expect(teams).toHaveLength(4);
  });

  it('should deduplicate teams across multiple services', () => {
    const teams = getTeamForServices(['Strategy Foundation', 'Brand Transformation']);
    // Both include strategy and PM, Brand adds branding
    const uniqueDepts = new Set(teams.map((t) => t.description));
    expect(uniqueDepts.size).toBe(teams.length);
  });

  it('should generate German team paragraph', () => {
    const paragraph = generateTeamParagraph(['Strategy Foundation'], 'DE');
    expect(paragraph).toContain('integrierten Team');
    expect(paragraph).toContain('Moritz Gruber');
  });

  it('should generate Italian team paragraph', () => {
    const paragraph = generateTeamParagraph(['Brand Transformation'], 'IT');
    expect(paragraph).toContain('team integrato');
  });

  it('should generate English team paragraph', () => {
    const paragraph = generateTeamParagraph(['Digital Growth'], 'EN');
    expect(paragraph).toContain('integrated team');
  });
});

describe('Project Phase Generator', () => {
  it('should generate phases for Strategy Foundation', () => {
    const plan = generateProjectPlan({
      services: ['Strategy Foundation'],
      budget: '10-20k',
      timeline: '3-6 Monate',
      isRetainer: false,
    });

    expect(plan.phases.length).toBeGreaterThanOrEqual(3);
    expect(plan.isRetainer).toBe(false);
    expect(plan.totalPrice).toBeGreaterThan(0);

    // Each phase should have a price
    for (const phase of plan.phases) {
      expect(phase.price).toBeGreaterThan(0);
      expect(phase.title).toBeTruthy();
      expect(phase.fokuspunkte.length).toBeGreaterThan(0);
    }
  });

  it('should generate retainer plan for Full-Service Partner', () => {
    const plan = generateProjectPlan({
      services: ['Full-Service Partner'],
      budget: '>50k',
      timeline: 'Retainer',
      isRetainer: true,
    });

    expect(plan.isRetainer).toBe(true);
    expect(plan.totalPrice).toBe(12000); // Full-Service = €12k/month
  });

  it('should generate phases for AI Audit', () => {
    const plan = generateProjectPlan({
      services: ['AI Audit'],
      budget: '<5k',
      timeline: '1-3 Monate',
      isRetainer: false,
    });

    expect(plan.phases.length).toBeGreaterThanOrEqual(2);
    expect(plan.totalPrice).toBeLessThanOrEqual(5000);
  });

  it('should combine phases for multiple services', () => {
    const plan = generateProjectPlan({
      services: ['Brand Transformation', 'Content Engine'],
      budget: '20-50k',
      timeline: '6-12 Monate',
      isRetainer: false,
    });

    // Should have phases from both services
    expect(plan.phases.length).toBeGreaterThanOrEqual(4);
  });
});

describe('Proposal Model', () => {
  it('should generate correct document title', () => {
    const title = generateDocTitle('TechCorp GmbH');
    expect(title).toMatch(/^Angebot_TechCorp_GmbH_\d{4}-\d{2}-\d{2}$/);
  });

  it('should create empty proposal with correct defaults', () => {
    const proposal = createEmptyProposal('task-123', 'DE');
    expect(proposal.id).toContain('task-123');
    expect(proposal.language).toBe('DE');
    expect(proposal.clickupTaskId).toBe('task-123');
    expect(proposal.references.portfolioLink).toBe('https://partner.zukunvt.it');
  });
});

describe('Template Parser', () => {
  it('should parse German proposal text', () => {
    const sampleText = `Anschreiben

Lieber Herr Müller, ich freue mich sehr, Ihnen unser Angebot zu senden.
Zusammen werden wir Ihre Marke auf das nächste Level bringen.


Rechtlicher Hinweis

Dieses Angebot ist 6 Wochen ab Erhalt gültig.
Es gelten unsere AGB.


Kalkulation

Phase 1: Discovery — €5.000
Phase 2: Strategy — €7.500


Zusammenfassung

Netto: €12.500
MwSt. 22%: €2.750
Brutto: €15.250
Zahlungsbedingungen: 50% Vorauszahlung, 50% bei Abschluss


Referenzen

Partner A — Tourism
Erfolgreiche Destination Marketing Kampagne.`;

    const parsed = parseProposalText(sampleText, 'DE');
    expect(parsed.language).toBe('DE');
    expect(parsed.sections.length).toBeGreaterThanOrEqual(4);

    const coverLetter = parsed.sections.find((s) => s.type === 'cover_letter');
    expect(coverLetter).toBeDefined();

    const calculation = parsed.sections.find((s) => s.type === 'calculation');
    expect(calculation).toBeDefined();
  });

  it('should extract pricing from calculation section', () => {
    const section = {
      title: 'Kalkulation',
      content: 'Phase 1: Discovery — €5.000\nPhase 2: Strategy — €7.500\nPhase 3: Design — €3.000',
      type: 'calculation' as const,
    };

    const pricing = extractPricingFromTemplate(section);
    expect(pricing.length).toBe(3);
    expect(pricing[0].price).toBe(5000);
    expect(pricing[1].price).toBe(7500);
  });
});

describe('End-to-End Test Scenarios', () => {
  it('Strategy Foundation für B2B: should produce valid project plan', () => {
    const plan = generateProjectPlan({
      services: STRATEGY_B2B_TASK.services,
      budget: STRATEGY_B2B_TASK.budget,
      timeline: STRATEGY_B2B_TASK.timeline,
      isRetainer: false,
    });

    expect(plan.phases.length).toBe(4); // Strategy Foundation has 4 phases
    expect(plan.totalPrice).toBeGreaterThanOrEqual(10000);
    expect(plan.totalPrice).toBeLessThanOrEqual(20000);
  });

  it('Full-Service Retainer: should produce retainer plan at €12k/month', () => {
    const plan = generateProjectPlan({
      services: FULLSERVICE_RETAINER_TASK.services,
      budget: FULLSERVICE_RETAINER_TASK.budget,
      timeline: FULLSERVICE_RETAINER_TASK.timeline,
      isRetainer: true,
    });

    expect(plan.isRetainer).toBe(true);
    expect(plan.totalPrice).toBe(12000);
  });

  it('Brand + Marketing Kombi: should combine phases', () => {
    const plan = generateProjectPlan({
      services: BRAND_MARKETING_KOMBI_TASK.services,
      budget: BRAND_MARKETING_KOMBI_TASK.budget,
      timeline: BRAND_MARKETING_KOMBI_TASK.timeline,
      isRetainer: false,
    });

    expect(plan.phases.length).toBeGreaterThanOrEqual(4);
  });

  it('AI Audit für Bestandskunden: should be within budget', () => {
    const plan = generateProjectPlan({
      services: AI_AUDIT_BESTANDSKUNDE_TASK.services,
      budget: AI_AUDIT_BESTANDSKUNDE_TASK.budget,
      timeline: AI_AUDIT_BESTANDSKUNDE_TASK.timeline,
      isRetainer: false,
    });

    expect(plan.totalPrice).toBeLessThanOrEqual(5000);
  });

  it('All test tasks should pass validation', () => {
    const tasks = [
      STRATEGY_B2B_TASK,
      FULLSERVICE_RETAINER_TASK,
      BRAND_MARKETING_KOMBI_TASK,
      AI_AUDIT_BESTANDSKUNDE_TASK,
    ];

    for (const task of tasks) {
      const result = validateTaskData(task);
      expect(result.valid).toBe(true);
    }
  });
});
