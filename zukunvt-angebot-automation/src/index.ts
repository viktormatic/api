/**
 * zukunvt Angebot Automation — Main Entry Point
 *
 * Can be run as:
 * 1. Standalone webhook server (listens for ClickUp task status changes)
 * 2. n8n Code Node (called from n8n workflow with task data)
 * 3. CLI for manual proposal generation
 */

import dotenv from 'dotenv';
import { ClickUpClient } from './clickup/client';
import { parseTaskData } from './clickup/custom-fields';
import { validateTaskData } from './models/client-data';
import { GoogleDriveClient } from './google/drive-client';
import { GoogleDocsClient } from './google/docs-client';
import { parseProposalText, generateTemplateContext } from './google/template-parser';
import { ProposalGenerator } from './ai/proposal-generator';
import { generateDocTitle } from './models/proposal';
import { createWebhookApp } from './clickup/webhook-handler';

dotenv.config();

/**
 * Environment configuration
 */
function loadConfig() {
  return {
    clickup: {
      apiToken: process.env.CLICKUP_API_TOKEN!,
      workspaceId: process.env.CLICKUP_WORKSPACE_ID!,
      listId: process.env.CLICKUP_LIST_ID!,
    },
    google: {
      serviceAccountKeyPath: process.env.GOOGLE_SERVICE_ACCOUNT_KEY!,
      driveFolderId: process.env.GOOGLE_DRIVE_FOLDER_ID!,
    },
    anthropic: {
      apiKey: process.env.ANTHROPIC_API_KEY!,
      model: process.env.CLAUDE_MODEL ?? 'claude-sonnet-4-20250514',
    },
    server: {
      port: parseInt(process.env.PORT ?? '3000', 10),
      webhookSecret: process.env.WEBHOOK_SECRET,
    },
    notificationEmail: process.env.NOTIFICATION_EMAIL ?? 'vm@zukunvt.com',
  };
}

/**
 * Initialize all service clients
 */
function initClients(config: ReturnType<typeof loadConfig>) {
  const clickup = new ClickUpClient({
    apiToken: config.clickup.apiToken,
    workspaceId: config.clickup.workspaceId,
    listId: config.clickup.listId,
  });

  const drive = new GoogleDriveClient({
    serviceAccountKeyPath: config.google.serviceAccountKeyPath,
    folderId: config.google.driveFolderId,
  });

  const docs = new GoogleDocsClient({
    serviceAccountKeyPath: config.google.serviceAccountKeyPath,
    folderId: config.google.driveFolderId,
  });

  const proposalGenerator = new ProposalGenerator({
    apiKey: config.anthropic.apiKey,
    model: config.anthropic.model,
  });

  return { clickup, drive, docs, proposalGenerator };
}

/**
 * Core proposal generation pipeline
 */
async function generateProposalForTask(
  taskId: string,
  clients: ReturnType<typeof initClients>,
  config: ReturnType<typeof loadConfig>
): Promise<{ docUrl: string; docId: string }> {
  const { clickup, drive, docs, proposalGenerator } = clients;

  console.log(`[Pipeline] Starting proposal generation for task ${taskId}`);

  // Step 1: Get task data from ClickUp
  console.log('[Step 1] Fetching task data from ClickUp...');
  const task = await clickup.getTask(taskId);
  const taskData = parseTaskData(task.id, task.name, task.custom_fields);

  const validation = validateTaskData(taskData);
  if (!validation.valid) {
    throw new Error(
      `Missing required fields: ${validation.missingFields.join(', ')}`
    );
  }

  // Step 2: Load reference templates from Google Drive
  console.log('[Step 2] Loading reference templates from Google Drive...');
  let templateContext: string | undefined;
  try {
    const references = await drive.loadReferenceProposals(taskData.sprache);
    if (references.length > 0) {
      const parsed = references.map((ref) =>
        parseProposalText(ref.content, taskData.sprache)
      );
      templateContext = generateTemplateContext(parsed);
    }
  } catch (error) {
    console.warn('[Step 2] Could not load templates, proceeding without:', error);
  }

  // Step 3: Generate proposal content via Claude AI
  console.log('[Step 3] Generating proposal content via Claude AI...');
  const proposal = await proposalGenerator.generateProposal(
    taskData,
    templateContext
  );

  // Step 4: Create Google Doc
  console.log('[Step 4] Creating Google Doc...');
  const docTitle = generateDocTitle(taskData.kundenName);
  const { docId, docUrl } = await docs.createProposalDoc(proposal, docTitle);

  proposal.googleDocId = docId;
  proposal.googleDocUrl = docUrl;

  // Step 5: Move to "Generierte Angebote" subfolder
  console.log('[Step 5] Organizing document in Drive...');
  try {
    await drive.moveToSubfolder(docId, 'Generierte Angebote');
  } catch (error) {
    console.warn('[Step 5] Could not move to subfolder:', error);
  }

  // Step 6: Update ClickUp task
  console.log('[Step 6] Updating ClickUp task...');
  await clickup.updateTaskStatus(taskId, 'to review (intern)');
  await clickup.addComment(taskId, {
    comment_text: `Angebot automatisch erstellt: ${docUrl}`,
    notify_all: true,
  });

  console.log(`[Pipeline] Proposal generated successfully: ${docUrl}`);
  return { docUrl, docId };
}

/**
 * Handle errors during proposal generation
 */
async function handlePipelineError(
  taskId: string,
  error: unknown,
  clickup: ClickUpClient,
  retryCount: number = 0
): Promise<void> {
  const errorMessage =
    error instanceof Error ? error.message : String(error);

  console.error(`[Pipeline Error] Task ${taskId}:`, errorMessage);

  // Retry up to 2 times for AI generation errors
  if (retryCount < 2 && errorMessage.includes('AI')) {
    console.log(`[Retry] Attempt ${retryCount + 1} for task ${taskId}`);
    return;
  }

  // Update ClickUp task status to BLOCKED
  try {
    await clickup.updateTaskStatus(taskId, 'blocked');
    await clickup.addComment(taskId, {
      comment_text: `Angebots-Automatisierung fehlgeschlagen: ${errorMessage}. Bitte manuell erstellen oder Fehler beheben und Status zurück auf "TO DO" setzen.`,
      notify_all: true,
    });
  } catch (updateError) {
    console.error('[Pipeline Error] Could not update ClickUp task:', updateError);
  }
}

/**
 * n8n Code Node export — called from n8n workflow
 */
export async function n8nHandler(input: {
  taskId: string;
}): Promise<{ success: boolean; docUrl?: string; error?: string }> {
  try {
    const config = loadConfig();
    const clients = initClients(config);

    const result = await generateProposalForTask(
      input.taskId,
      clients,
      config
    );

    return { success: true, docUrl: result.docUrl };
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : String(error);
    return { success: false, error: errorMessage };
  }
}

/**
 * Start standalone webhook server
 */
async function startServer(): Promise<void> {
  const config = loadConfig();
  const clients = initClients(config);

  const app = createWebhookApp({
    clickupClient: clients.clickup,
    webhookSecret: config.server.webhookSecret,
    onProposalTrigger: async (taskId: string) => {
      try {
        await generateProposalForTask(taskId, clients, config);
      } catch (error) {
        await handlePipelineError(taskId, error, clients.clickup);
      }
    },
  });

  app.listen(config.server.port, () => {
    console.log(
      `zukunvt Angebot Automation running on port ${config.server.port}`
    );
    console.log(`Webhook endpoint: POST /webhook/clickup`);
    console.log(`Manual trigger: POST /trigger/proposal`);
    console.log(`Health check: GET /health`);
  });
}

// CLI entry point
if (require.main === module) {
  const args = process.argv.slice(2);

  if (args[0] === '--task' && args[1]) {
    // Manual trigger: npx ts-node src/index.ts --task TASK_ID
    const config = loadConfig();
    const clients = initClients(config);
    generateProposalForTask(args[1], clients, config)
      .then((result) => {
        console.log('Proposal created:', result.docUrl);
        process.exit(0);
      })
      .catch((error) => {
        console.error('Failed:', error);
        process.exit(1);
      });
  } else {
    // Default: start webhook server
    startServer().catch((error) => {
      console.error('Failed to start server:', error);
      process.exit(1);
    });
  }
}

export { generateProposalForTask, loadConfig, initClients };
