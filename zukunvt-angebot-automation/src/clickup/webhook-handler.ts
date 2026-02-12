/**
 * ClickUp Webhook Handler
 * Express server that listens for ClickUp task status changes
 * and triggers proposal generation
 */

import express, { Request, Response } from 'express';
import crypto from 'crypto';
import { ClickUpClient } from './client';
import { parseTaskData } from './custom-fields';
import { validateTaskData } from '../models/client-data';

export interface WebhookPayload {
  event: string;
  task_id: string;
  history_items: Array<{
    field: string;
    before: { status: string } | string;
    after: { status: string } | string;
  }>;
  webhook_id: string;
}

export type ProposalGenerationCallback = (taskId: string) => Promise<void>;

/**
 * Create the webhook handler Express app
 */
export function createWebhookApp(config: {
  clickupClient: ClickUpClient;
  webhookSecret?: string;
  onProposalTrigger: ProposalGenerationCallback;
}): express.Application {
  const app = express();
  app.use(express.json());

  // Health check
  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok', service: 'zukunvt-angebot-automation' });
  });

  // ClickUp webhook endpoint
  app.post('/webhook/clickup', async (req: Request, res: Response) => {
    try {
      // Verify webhook signature if secret is configured
      if (config.webhookSecret) {
        const signature = req.headers['x-signature'] as string;
        if (!verifySignature(JSON.stringify(req.body), config.webhookSecret, signature)) {
          res.status(401).json({ error: 'Invalid signature' });
          return;
        }
      }

      const payload = req.body as WebhookPayload;

      // Only process taskStatusUpdated events
      if (payload.event !== 'taskStatusUpdated') {
        res.json({ status: 'ignored', reason: 'not a status update event' });
        return;
      }

      // Check if the status changed TO "to do"
      const statusChange = payload.history_items.find(
        (item) => item.field === 'status'
      );

      if (!statusChange) {
        res.json({ status: 'ignored', reason: 'no status change found' });
        return;
      }

      const newStatus =
        typeof statusChange.after === 'object'
          ? statusChange.after.status
          : statusChange.after;

      if (newStatus.toLowerCase() !== 'to do') {
        res.json({
          status: 'ignored',
          reason: `status changed to "${newStatus}", not "to do"`,
        });
        return;
      }

      // Fetch task details and validate
      const task = await config.clickupClient.getTask(payload.task_id);
      const taskData = parseTaskData(task.id, task.name, task.custom_fields);
      const validation = validateTaskData(taskData);

      if (!validation.valid) {
        // Update task status to "NEEDS INPUT" and add comment
        await config.clickupClient.updateTaskStatus(
          payload.task_id,
          'needs input'
        );
        await config.clickupClient.addComment(payload.task_id, {
          comment_text: `Angebots-Automatisierung: Folgende Pflichtfelder fehlen: ${validation.missingFields.join(', ')}. Bitte ergänzen und Status zurück auf "TO DO" setzen.`,
          notify_all: true,
        });

        res.json({
          status: 'needs_input',
          missingFields: validation.missingFields,
        });
        return;
      }

      // Trigger proposal generation asynchronously
      config.onProposalTrigger(payload.task_id).catch((error) => {
        console.error(
          `Proposal generation failed for task ${payload.task_id}:`,
          error
        );
      });

      res.json({ status: 'processing', taskId: payload.task_id });
    } catch (error) {
      console.error('Webhook processing error:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });

  // n8n trigger endpoint (alternative to ClickUp webhook)
  app.post('/trigger/proposal', async (req: Request, res: Response) => {
    try {
      const { taskId } = req.body;
      if (!taskId) {
        res.status(400).json({ error: 'taskId is required' });
        return;
      }

      config.onProposalTrigger(taskId).catch((error) => {
        console.error(`Proposal generation failed for task ${taskId}:`, error);
      });

      res.json({ status: 'processing', taskId });
    } catch (error) {
      console.error('Trigger error:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });

  return app;
}

/**
 * Verify ClickUp webhook signature
 */
function verifySignature(
  body: string,
  secret: string,
  signature: string
): boolean {
  if (!signature) return false;
  const hmac = crypto.createHmac('sha256', secret).update(body).digest('hex');
  return crypto.timingSafeEqual(Buffer.from(hmac), Buffer.from(signature));
}
