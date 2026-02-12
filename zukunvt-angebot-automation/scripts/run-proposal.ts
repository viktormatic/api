#!/usr/bin/env npx ts-node
/**
 * Standalone Proposal Runner
 *
 * Usage:
 *   cd zukunvt-angebot-automation
 *   npx ts-node scripts/run-proposal.ts 86c84phpu
 *
 * What it does:
 *   1. Fetches task from ClickUp API (custom fields)
 *   2. Generates project phases based on services & budget
 *   3. Calls Claude API to generate proposal content
 *   4. Creates a Google Doc with formatted proposal
 *   5. Updates ClickUp task (status → "TO REVIEW (INTERN)", adds doc link)
 *
 * Requirements:
 *   - .env file with CLICKUP_API_TOKEN (required)
 *   - .env file with ANTHROPIC_API_KEY (required for AI generation)
 *   - .env file with GOOGLE_SERVICE_ACCOUNT_KEY (required for Google Docs)
 *
 * Modes:
 *   --fetch-only     Only fetch and display task data, don't generate
 *   --skip-google    Generate proposal but skip Google Docs creation
 *   --skip-clickup   Don't update ClickUp task status
 *   --output <file>  Write proposal JSON to file
 */

import dotenv from 'dotenv';
import axios from 'axios';
import path from 'path';
import fs from 'fs';

dotenv.config({ path: path.resolve(__dirname, '../.env') });

// ─── Imports from the main project ───────────────────────────────────
import { parseTaskData, FIELD_NAMES } from '../src/clickup/custom-fields';
import { validateTaskData, AngebotTaskData } from '../src/models/client-data';
import { generateProjectPlan } from '../src/ai/phase-planner';
import { generateTeamParagraph, ServiceType } from '../src/config/team';
import { PRICING_2026, calculateVat, getPaymentTerms, VatRegion } from '../src/config/pricing';
import { LEGAL_TEMPLATES, SIGNATURE_TEMPLATE, INDUSTRY_REFERENCES } from '../src/config/templates';
import {
  Proposal,
  createEmptyProposal,
  generateDocTitle,
} from '../src/models/proposal';

// ─── CLI Arguments ───────────────────────────────────────────────────
const args = process.argv.slice(2);
const taskId = args.find((a) => !a.startsWith('--'));
const fetchOnly = args.includes('--fetch-only');
const skipGoogle = args.includes('--skip-google');
const skipClickup = args.includes('--skip-clickup');
const outputIdx = args.indexOf('--output');
const outputFile = outputIdx >= 0 ? args[outputIdx + 1] : null;

if (!taskId) {
  console.error('Usage: npx ts-node scripts/run-proposal.ts <TASK_ID> [options]');
  console.error('');
  console.error('Options:');
  console.error('  --fetch-only     Only fetch and display task data');
  console.error('  --skip-google    Skip Google Docs creation');
  console.error('  --skip-clickup   Skip ClickUp status update');
  console.error('  --output <file>  Write proposal JSON to file');
  process.exit(1);
}

const CLICKUP_TOKEN = process.env.CLICKUP_API_TOKEN;
if (!CLICKUP_TOKEN) {
  console.error('ERROR: CLICKUP_API_TOKEN not set in .env');
  process.exit(1);
}

// ─── ClickUp API Helper ─────────────────────────────────────────────
const clickupApi = axios.create({
  baseURL: 'https://api.clickup.com/api/v2',
  headers: {
    Authorization: CLICKUP_TOKEN,
    'Content-Type': 'application/json',
  },
});

async function fetchTask(id: string) {
  console.log(`\n📋 Fetching ClickUp task ${id}...`);
  const { data } = await clickupApi.get(`/task/${id}`, {
    params: { custom_task_ids: false, include_subtasks: false },
  });
  return data;
}

async function updateTaskStatus(id: string, status: string) {
  await clickupApi.put(`/task/${id}`, { status });
}

async function addTaskComment(id: string, text: string) {
  await clickupApi.post(`/task/${id}/comment`, {
    comment_text: text,
    notify_all: true,
  });
}

async function setCustomField(taskIdParam: string, fieldId: string, value: string) {
  await clickupApi.post(`/task/${taskIdParam}/field/${fieldId}`, { value });
}

// ─── VAT Region Detection ───────────────────────────────────────────
function detectVatRegion(taskData: AngebotTaskData): VatRegion {
  const notizen = (taskData.notizen ?? '').toLowerCase();
  if (
    notizen.includes('österreich') || notizen.includes('austria') ||
    notizen.includes('wien') || notizen.includes('vienna')
  ) return 'austria';
  if (
    notizen.includes('italien') || notizen.includes('italy') ||
    notizen.includes('südtirol') || notizen.includes('alto adige') ||
    taskData.sprache === 'IT'
  ) return 'italy';
  return 'euReverseCharge';
}

// ─── Proposal Assembly (without AI — uses templates) ────────────────
function assembleProposalFromTemplates(taskData: AngebotTaskData): Proposal {
  const lang = taskData.sprache;
  const isRetainer = taskData.timeline === 'Retainer';

  // Generate project plan
  const projectPlan = generateProjectPlan({
    services: taskData.services,
    budget: taskData.budget,
    timeline: taskData.timeline,
    isRetainer,
  });

  // Create proposal
  const proposal = createEmptyProposal(taskData.taskId, lang);

  // Cover letter (template-based)
  const greetingMap = {
    DE: `Liebe/r ${taskData.ansprechpartner},`,
    IT: `Gentile ${taskData.ansprechpartner},`,
    EN: `Dear ${taskData.ansprechpartner},`,
  };
  const bodyMap = {
    DE: `ich freue mich sehr, Ihnen wie vereinbart das Angebot für unsere potenzielle Kollaboration zuzusenden.\n\nBasierend auf unserem Gespräch verstehen wir, dass ${taskData.kundenName} Unterstützung in den Bereichen ${taskData.services.join(', ')} benötigt. ${taskData.projektBeschreibung}\n\nAls internationale Markenberatung mit über 10 Jahren Erfahrung verbinden wir Strategie, Marke und Marketing zu einem integrierten Ansatz — genau das, was ${taskData.kundenName} braucht, um die nächste Stufe zu erreichen. Wir sehen großes Potenzial in einer gemeinsamen Zusammenarbeit und würden uns freuen, ${taskData.kundenName} als Partner begleiten zu dürfen.`,
    IT: `sono molto lieto di inviarLe, come concordato, l'offerta per la nostra potenziale collaborazione.\n\nDalla nostra conversazione abbiamo compreso che ${taskData.kundenName} necessita di supporto nelle aree ${taskData.services.join(', ')}. ${taskData.projektBeschreibung}\n\nCome consulenza internazionale di marca con oltre 10 anni di esperienza, uniamo strategia, marca e marketing in un approccio integrato. Vediamo un grande potenziale nella nostra collaborazione e saremmo lieti di accompagnare ${taskData.kundenName} come partner.`,
    EN: `I am delighted to send you, as discussed, the proposal for our potential collaboration.\n\nBased on our conversation, we understand that ${taskData.kundenName} needs support in the areas of ${taskData.services.join(', ')}. ${taskData.projektBeschreibung}\n\nAs an international brand consultancy with over 10 years of experience, we combine strategy, brand, and marketing into an integrated approach. We see great potential in working together and would be honored to accompany ${taskData.kundenName} as a partner.`,
  };
  const closingMap = {
    DE: `Wir freuen uns auf die gemeinsame Zusammenarbeit und stehen für Rückfragen jederzeit zur Verfügung.\n\nHerzliche Grüße,\nViktor Matic & das zukunvt Team`,
    IT: `Non vediamo l'ora di collaborare insieme e siamo a disposizione per qualsiasi domanda.\n\nCordiali saluti,\nViktor Matic & il team zukunvt`,
    EN: `We look forward to working together and are available for any questions.\n\nBest regards,\nViktor Matic & the zukunvt team`,
  };

  proposal.coverLetter = {
    greeting: greetingMap[lang],
    body: bodyMap[lang],
    teamParagraph: generateTeamParagraph(taskData.services as ServiceType[], lang),
    closing: closingMap[lang],
  };

  // Legal notice
  proposal.legalNotice = LEGAL_TEMPLATES[lang];

  // Calculation
  proposal.calculation = {
    rows: projectPlan.phases.map((phase) => ({
      nr: phase.phaseNumber,
      title: phase.title,
      price: phase.price,
      details: {
        fokuspunkte: phase.fokuspunkte,
        inhalt: phase.inhalt,
        phasenziel: phase.phasenziel,
        output: phase.output,
      },
    })),
    projectPhases: projectPlan.phases,
  };

  // Summary
  const netTotal = projectPlan.totalPrice;
  const vatRegion = detectVatRegion(taskData);
  const vatAmount = calculateVat(netTotal, vatRegion);
  const paymentTermsConfig = getPaymentTerms(netTotal, isRetainer);

  proposal.summary = {
    financials: {
      netTotal,
      vatRate: PRICING_2026.vat[vatRegion],
      vatAmount,
      grossTotal: netTotal + vatAmount,
    },
    paymentTerms: paymentTermsConfig.installments.map((inst) => ({
      percentage: inst.percentage,
      amount: Math.round((netTotal * inst.percentage) / 100),
      label: inst.label,
    })),
    inclusions: [
      'Alle genannten Workshops und Meetings',
      'Projektmanagement und laufende Abstimmung',
      'Alle definierten Deliverables und Outputs',
      'Korrekturschleifen (max. 2 pro Deliverable)',
    ],
    exclusions: [
      'Reisekosten (werden nach Aufwand verrechnet, €0,85/km)',
      'Externe Produktionskosten (Druck, Foto, Video)',
      'Lizenzgebühren für Stockmaterial',
      'Zusätzliche Leistungen außerhalb des Scopes',
    ],
    signatureSection: {
      agreementText: SIGNATURE_TEMPLATE[lang].agreementText,
      agencyName: 'zukunvt GmbH',
      partnerName: taskData.kundenName,
    },
  };

  // References
  const industryRefs = INDUSTRY_REFERENCES[taskData.branche] ?? INDUSTRY_REFERENCES['B2B'] ?? [];
  proposal.references = {
    entries: industryRefs.slice(0, 3).map((desc) => ({
      partnerName: 'zukunvt Partner',
      industry: taskData.branche,
      description: desc,
    })),
    portfolioLink: 'https://partner.zukunvt.it',
  };

  // Metadata
  proposal.metadata = {
    kundenName: taskData.kundenName,
    ansprechpartner: taskData.ansprechpartner,
    services: taskData.services,
    branche: taskData.branche,
    isRetainer,
    generatedBy: 'zukunvt-angebot-automation (template-mode)',
  };

  return proposal;
}

// ─── Pretty Print ───────────────────────────────────────────────────
function printTaskSummary(task: any, taskData: AngebotTaskData) {
  console.log('\n══════════════════════════════════════════════════════');
  console.log(`📋 Task: ${task.name}`);
  console.log(`🔗 URL: ${task.url}`);
  console.log(`📊 Status: ${task.status?.status ?? 'unknown'}`);
  console.log('══════════════════════════════════════════════════════');
  console.log(`  Kundenname:        ${taskData.kundenName}`);
  console.log(`  Ansprechpartner:   ${taskData.ansprechpartner}`);
  console.log(`  E-Mail:            ${taskData.email}`);
  console.log(`  Services:          ${taskData.services.join(', ') || '(none)'}`);
  console.log(`  Branche:           ${taskData.branche}`);
  console.log(`  Budget:            ${taskData.budget}`);
  console.log(`  Timeline:          ${taskData.timeline}`);
  console.log(`  Sprache:           ${taskData.sprache}`);
  console.log(`  Bestandskunde:     ${taskData.bestehenderKunde ? 'Ja' : 'Nein'}`);
  console.log(`  Notizen:           ${taskData.notizen || '(keine)'}`);
  console.log(`  Projektbeschr.:    ${taskData.projektBeschreibung || '(keine)'}`);
  console.log('══════════════════════════════════════════════════════\n');
}

function printProposalSummary(proposal: Proposal) {
  const { financials } = proposal.summary;
  console.log('\n══════════════════════════════════════════════════════');
  console.log('📄 GENERIERTES ANGEBOT');
  console.log('══════════════════════════════════════════════════════');
  console.log(`  Sprache:       ${proposal.language}`);
  console.log(`  Für:           ${proposal.metadata.kundenName}`);
  console.log(`  Services:      ${proposal.metadata.services.join(', ')}`);
  console.log(`  Retainer:      ${proposal.metadata.isRetainer ? 'Ja' : 'Nein'}`);
  console.log('──────────────────────────────────────────────────────');
  console.log('  KALKULATION:');
  for (const row of proposal.calculation.rows) {
    console.log(`    ${row.nr}. ${row.title.padEnd(35)} €${row.price.toLocaleString('de-DE')}`);
  }
  console.log('──────────────────────────────────────────────────────');
  console.log(`  Netto:         €${financials.netTotal.toLocaleString('de-DE')}`);
  console.log(`  MwSt. (${(financials.vatRate * 100).toFixed(0)}%):   €${financials.vatAmount.toLocaleString('de-DE')}`);
  console.log(`  Brutto:        €${financials.grossTotal.toLocaleString('de-DE')}`);
  console.log('──────────────────────────────────────────────────────');
  console.log('  ZAHLUNGSBEDINGUNGEN:');
  for (const term of proposal.summary.paymentTerms) {
    console.log(`    ${term.percentage}% (€${term.amount.toLocaleString('de-DE')}): ${term.label}`);
  }
  console.log('──────────────────────────────────────────────────────');
  console.log('  PROJEKTPHASEN:');
  for (const phase of proposal.calculation.projectPhases) {
    console.log(`    Phase ${phase.phaseNumber}: ${phase.title} (${phase.timeRange})`);
    console.log(`      Fokus: ${phase.fokuspunkte.join(', ')}`);
    console.log(`      Output: ${phase.output.join(', ')}`);
  }
  console.log('══════════════════════════════════════════════════════\n');
}

// ─── Main ───────────────────────────────────────────────────────────
async function main() {
  try {
    // Step 1: Fetch task from ClickUp
    const task = await fetchTask(taskId!);
    const taskData = parseTaskData(task.id, task.name, task.custom_fields || []);

    printTaskSummary(task, taskData);

    // Validate
    const validation = validateTaskData(taskData);
    if (!validation.valid) {
      console.warn(`⚠️  Missing fields: ${validation.missingFields.join(', ')}`);
      console.warn('   Proceeding with available data...\n');
    }

    if (fetchOnly) {
      console.log('✅ Fetch-only mode. Raw custom fields:');
      console.log(JSON.stringify(task.custom_fields, null, 2));
      return;
    }

    // Step 2: Generate proposal (template-based, no AI needed)
    console.log('🔧 Generating proposal from templates...');
    const proposal = assembleProposalFromTemplates(taskData);

    printProposalSummary(proposal);

    // Step 3: If we have Anthropic key, enhance with AI
    if (process.env.ANTHROPIC_API_KEY) {
      console.log('🤖 Anthropic API key found — enhancing with AI...');
      const { ProposalGenerator } = await import('../src/ai/proposal-generator');
      const generator = new ProposalGenerator({
        apiKey: process.env.ANTHROPIC_API_KEY,
        model: process.env.CLAUDE_MODEL,
      });
      const aiProposal = await generator.generateProposal(taskData);
      Object.assign(proposal, {
        coverLetter: aiProposal.coverLetter,
        references: aiProposal.references,
      });
      // Keep our calculated financials (more reliable)
      console.log('✅ AI enhancement complete');
    } else {
      console.log('ℹ️  No ANTHROPIC_API_KEY — using template-based content');
    }

    // Step 4: Create Google Doc (if credentials exist)
    let docUrl: string | null = null;
    if (!skipGoogle && fs.existsSync(path.resolve(process.env.GOOGLE_SERVICE_ACCOUNT_KEY || ''))) {
      console.log('📄 Creating Google Doc...');
      const { GoogleDocsClient } = await import('../src/google/docs-client');
      const docsClient = new GoogleDocsClient({
        serviceAccountKeyPath: process.env.GOOGLE_SERVICE_ACCOUNT_KEY!,
        folderId: process.env.GOOGLE_DRIVE_FOLDER_ID!,
      });
      const docTitle = generateDocTitle(taskData.kundenName);
      const result = await docsClient.createProposalDoc(proposal, docTitle);
      docUrl = result.docUrl;
      proposal.googleDocId = result.docId;
      proposal.googleDocUrl = result.docUrl;
      console.log(`✅ Google Doc created: ${docUrl}`);
    } else {
      console.log('ℹ️  Skipping Google Docs (no credentials or --skip-google)');
    }

    // Step 5: Update ClickUp task
    if (!skipClickup) {
      console.log('🔄 Updating ClickUp task...');
      try {
        await updateTaskStatus(taskId!, 'to review (intern)');
        const commentText = docUrl
          ? `Angebot automatisch erstellt: ${docUrl}`
          : `Angebot automatisch generiert (Proposal JSON bereit). Google Doc Erstellung ausstehend.`;
        await addTaskComment(taskId!, commentText);
        console.log('✅ ClickUp updated → status: "TO REVIEW (INTERN)"');
      } catch (err: any) {
        console.warn(`⚠️  Could not update ClickUp: ${err.message}`);
      }
    }

    // Step 6: Write output
    if (outputFile) {
      fs.writeFileSync(outputFile, JSON.stringify(proposal, null, 2));
      console.log(`💾 Proposal JSON saved to: ${outputFile}`);
    }

    // Always save a copy
    const outputDir = path.resolve(__dirname, '../output');
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
    const autoOutputFile = path.join(
      outputDir,
      `proposal_${taskData.kundenName.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.json`
    );
    fs.writeFileSync(autoOutputFile, JSON.stringify(proposal, null, 2));
    console.log(`💾 Auto-saved: ${autoOutputFile}`);

    console.log('\n✅ Done!\n');
  } catch (error: any) {
    console.error('\n❌ Error:', error.message);
    if (error.response?.data) {
      console.error('API Response:', JSON.stringify(error.response.data, null, 2));
    }
    process.exit(1);
  }
}

main();
