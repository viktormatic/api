/**
 * Proposal Generator
 * Uses Claude API to generate proposal content based on client data and templates
 */

import Anthropic from '@anthropic-ai/sdk';
import { AngebotTaskData, Language } from '../models/client-data';
import {
  Proposal,
  ProposalCalculationRow,
  ProposalSummary,
  ReferenceEntry,
  createEmptyProposal,
  generateDocTitle,
} from '../models/proposal';
import { ProjectPhase } from '../models/project-phase';
import { generateProjectPlan } from './phase-planner';
import { PRICING_2026, calculateVat, getPaymentTerms, VatRegion } from '../config/pricing';
import { generateTeamParagraph, ServiceType } from '../config/team';
import { LEGAL_TEMPLATES, SIGNATURE_TEMPLATE, INDUSTRY_REFERENCES } from '../config/templates';

const SYSTEM_PROMPT = `Du bist der Angebots-Generator der zukunvt Agentur — eine internationale Markenberatung
mit Sitz in Südtirol und Wien (10+ Jahre Erfahrung).

KERNPHILOSOPHIE: "Strategie, Marke und Marketing müssen als Einheit zusammenwirken."

SPRACHE & TON:
- Professionell aber warm und persönlich
- Kollaborativ: "zusammen", "gemeinsam", "co-creation", "mit Ihnen"
- Kunden = "Partner" (NIEMALS "Kunden" oder "Clients")
- Mehrsprachig: Hauptsprache nach Anforderung (DE/IT/EN)
- Deutsch: Verwende zukunvt-Terminologie: Positionierung, Wertangebot,
  Zielgruppen, Kommunikationsplan, Gewünschte Ergebnisse, Umsetzung

REGELN:
- Strategie/Branding/Marketing NIEMALS als getrennte Bereiche darstellen → immer integriert
- Drei Signaturprozesse kennen und korrekt einsetzen:
  1. Strategy Foundation: BMC, Wertangebot, OKRs, USP
  2. Brand Transformation: Positionierung, Brand Architecture, Kommunikationsplan, ToV
  3. Agile Activation: Lead Gen, Customer Journey, Content Calendar, KPI-Sprints
- Preise EXAKT aus der 2026-Preisliste übernehmen
- Projektphasen mit konkreten Zeitangaben und Deliverables
- Immer passende Team-Mitglieder zuordnen

WICHTIG: Antworte IMMER im JSON-Format wie angegeben. Keine zusätzlichen Erklärungen außerhalb des JSON.`;

interface GeneratedContent {
  coverLetter: {
    greeting: string;
    body: string;
    closing: string;
  };
  calculationDescriptions: Array<{
    phaseTitle: string;
    fokuspunkte: string[];
    inhalt: string[];
    phasenziel: string;
    output: string[];
  }>;
  inclusions: string[];
  exclusions: string[];
  references: ReferenceEntry[];
}

export class ProposalGenerator {
  private anthropic: Anthropic;
  private model: string;

  constructor(config: {
    apiKey: string;
    model?: string;
  }) {
    this.anthropic = new Anthropic({ apiKey: config.apiKey });
    this.model = config.model ?? 'claude-sonnet-4-20250514';
  }

  /**
   * Generate a complete proposal from task data
   */
  async generateProposal(
    taskData: AngebotTaskData,
    templateContext?: string
  ): Promise<Proposal> {
    const proposal = createEmptyProposal(taskData.taskId, taskData.sprache);

    // 1. Generate project phases
    const isRetainer = taskData.timeline === 'Retainer';
    const projectPlan = generateProjectPlan({
      services: taskData.services,
      budget: taskData.budget,
      timeline: taskData.timeline,
      isRetainer,
    });

    // 2. Generate AI content (cover letter, descriptions, references)
    const aiContent = await this.generateAIContent(taskData, projectPlan.phases, templateContext);

    // 3. Assemble the proposal
    this.assembleProposal(proposal, taskData, projectPlan.phases, aiContent);

    // Set metadata
    proposal.metadata = {
      kundenName: taskData.kundenName,
      ansprechpartner: taskData.ansprechpartner,
      services: taskData.services,
      branche: taskData.branche,
      isRetainer,
      generatedBy: 'zukunvt-angebot-automation',
    };

    return proposal;
  }

  /**
   * Call Claude API to generate proposal content
   */
  private async generateAIContent(
    taskData: AngebotTaskData,
    phases: ProjectPhase[],
    templateContext?: string
  ): Promise<GeneratedContent> {
    const userPrompt = this.buildUserPrompt(taskData, phases, templateContext);

    const response = await this.anthropic.messages.create({
      model: this.model,
      max_tokens: 4096,
      system: SYSTEM_PROMPT,
      messages: [{ role: 'user', content: userPrompt }],
    });

    const textContent = response.content.find((c) => c.type === 'text');
    if (!textContent || textContent.type !== 'text') {
      throw new Error('No text content in AI response');
    }

    // Parse JSON from the response
    const jsonMatch = textContent.text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error('Could not parse JSON from AI response');
    }

    return JSON.parse(jsonMatch[0]) as GeneratedContent;
  }

  /**
   * Build the user prompt for Claude API
   */
  private buildUserPrompt(
    taskData: AngebotTaskData,
    phases: ProjectPhase[],
    templateContext?: string
  ): string {
    const phaseSummary = phases
      .map(
        (p) =>
          `Phase ${p.phaseNumber}: ${p.title} (${p.timeRange}) — €${p.price}`
      )
      .join('\n');

    return `Erstelle ein zukunvt-Angebot für folgenden Partner:

KUNDENDATEN:
- Firma: ${taskData.kundenName}
- Ansprechpartner: ${taskData.ansprechpartner}
- Branche: ${taskData.branche}
- Projektbeschreibung: ${taskData.projektBeschreibung}
- Bestandskunde: ${taskData.bestehenderKunde ? 'Ja' : 'Nein'}
${taskData.notizen ? `- Interne Notizen: ${taskData.notizen}` : ''}

GEWÜNSCHTE SERVICES: ${taskData.services.join(', ')}
BUDGET-RAHMEN: ${taskData.budget}
TIMELINE: ${taskData.timeline}
SPRACHE: ${taskData.sprache}

PROJEKTPHASEN (bereits kalkuliert):
${phaseSummary}

${templateContext ? `REFERENZ-KONTEXT:\n${templateContext}\n` : ''}

Antworte im folgenden JSON-Format:
{
  "coverLetter": {
    "greeting": "Persönliche Anrede an ${taskData.ansprechpartner}",
    "body": "2-3 Absätze: Bezug auf Discovery, Bedarf, warum zukunvt der richtige Partner ist. WICHTIG: Kollaborativer Ton, 'Partner' statt 'Kunde'.",
    "closing": "Professioneller Abschluss mit Vorfreude auf Zusammenarbeit"
  },
  "calculationDescriptions": [
    {
      "phaseTitle": "Phase-Titel",
      "fokuspunkte": ["Punkt 1", "Punkt 2"],
      "inhalt": ["Workshop/Meeting/Deliverable"],
      "phasenziel": "Was soll erreicht werden",
      "output": ["Konkretes Ergebnis 1", "Konkretes Ergebnis 2"]
    }
  ],
  "inclusions": ["Was ist im Angebot inkludiert"],
  "exclusions": ["Was ist NICHT inkludiert"],
  "references": [
    {
      "partnerName": "Firmenname",
      "industry": "Branche",
      "description": "Kurze Projektbeschreibung",
      "testimonial": "Optional: Zitat des Partners"
    }
  ]
}`;
  }

  /**
   * Assemble all parts into the final proposal
   */
  private assembleProposal(
    proposal: Proposal,
    taskData: AngebotTaskData,
    phases: ProjectPhase[],
    aiContent: GeneratedContent
  ): void {
    const lang = taskData.sprache;

    // Section 1: Cover Letter
    proposal.coverLetter = {
      greeting: aiContent.coverLetter.greeting,
      body: aiContent.coverLetter.body,
      teamParagraph: generateTeamParagraph(taskData.services as ServiceType[], lang),
      closing: aiContent.coverLetter.closing,
    };

    // Section 2: Legal Notice
    proposal.legalNotice = LEGAL_TEMPLATES[lang];

    // Section 3: Calculation
    proposal.calculation = {
      rows: phases.map((phase, index) => {
        const aiDesc = aiContent.calculationDescriptions[index];
        return {
          nr: phase.phaseNumber,
          title: phase.title,
          price: phase.price,
          details: aiDesc
            ? {
                fokuspunkte: aiDesc.fokuspunkte,
                inhalt: aiDesc.inhalt,
                phasenziel: aiDesc.phasenziel,
                output: aiDesc.output,
              }
            : {
                fokuspunkte: phase.fokuspunkte,
                inhalt: phase.inhalt,
                phasenziel: phase.phasenziel,
                output: phase.output,
              },
        };
      }),
      projectPhases: phases,
    };

    // Section 4: Summary & Terms
    const netTotal = phases.reduce((sum, p) => sum + p.price, 0);
    const vatRegion = this.getVatRegion(taskData);
    const vatAmount = calculateVat(netTotal, vatRegion);
    const isRetainer = taskData.timeline === 'Retainer';
    const paymentTermsConfig = getPaymentTerms(netTotal, isRetainer);

    const financials: ProposalSummary = {
      netTotal,
      vatRate: PRICING_2026.vat[vatRegion],
      vatAmount,
      grossTotal: netTotal + vatAmount,
    };

    proposal.summary = {
      financials,
      paymentTerms: paymentTermsConfig.installments.map((inst) => ({
        percentage: inst.percentage,
        amount: Math.round((netTotal * inst.percentage) / 100),
        label: inst.label,
      })),
      inclusions: aiContent.inclusions,
      exclusions: aiContent.exclusions,
      signatureSection: {
        agreementText: SIGNATURE_TEMPLATE[lang].agreementText,
        agencyName: 'zukunvt GmbH',
        partnerName: taskData.kundenName,
      },
    };

    // Section 5: References
    const industryRefs = INDUSTRY_REFERENCES[taskData.branche] ?? [];
    proposal.references = {
      entries:
        aiContent.references.length > 0
          ? aiContent.references
          : industryRefs.map((desc) => ({
              partnerName: 'zukunvt Partner',
              industry: taskData.branche,
              description: desc,
            })),
      portfolioLink: 'https://partner.zukunvt.it',
    };
  }

  /**
   * Determine VAT region from task data
   */
  private getVatRegion(taskData: AngebotTaskData): VatRegion {
    // Default logic: Italian company → IT VAT, Austrian → AT VAT, others → EU Reverse Charge
    const branche = taskData.branche.toLowerCase();
    const notizen = (taskData.notizen ?? '').toLowerCase();
    const name = taskData.kundenName.toLowerCase();

    if (
      notizen.includes('österreich') ||
      notizen.includes('austria') ||
      notizen.includes('wien') ||
      notizen.includes('vienna')
    ) {
      return 'austria';
    }

    if (
      notizen.includes('italien') ||
      notizen.includes('italy') ||
      notizen.includes('südtirol') ||
      notizen.includes('alto adige') ||
      taskData.sprache === 'IT'
    ) {
      return 'italy';
    }

    // Default to EU Reverse Charge for international partners
    return 'euReverseCharge';
  }
}
