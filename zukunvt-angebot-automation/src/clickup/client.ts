/**
 * ClickUp API v2 Client
 * Handles task reading, updating, and status management
 */

import axios, { AxiosInstance } from 'axios';

export interface ClickUpTask {
  id: string;
  name: string;
  status: {
    status: string;
    type: string;
  };
  custom_fields: ClickUpCustomField[];
  assignees: Array<{ id: number; username: string; email: string }>;
  url: string;
}

export interface ClickUpCustomField {
  id: string;
  name: string;
  type: string;
  value: unknown;
  type_config?: {
    options?: Array<{ id: string; name: string; label: string }>;
  };
}

export interface ClickUpComment {
  comment_text: string;
  assignee?: number;
  notify_all?: boolean;
}

export class ClickUpClient {
  private client: AxiosInstance;
  private workspaceId: string;
  private listId: string;

  constructor(config: {
    apiToken: string;
    workspaceId: string;
    listId: string;
  }) {
    this.workspaceId = config.workspaceId;
    this.listId = config.listId;
    this.client = axios.create({
      baseURL: 'https://api.clickup.com/api/v2',
      headers: {
        Authorization: config.apiToken,
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Get a task by ID with all custom fields
   */
  async getTask(taskId: string): Promise<ClickUpTask> {
    const response = await this.client.get(`/task/${taskId}`, {
      params: {
        custom_task_ids: false,
        include_subtasks: false,
      },
    });
    return response.data;
  }

  /**
   * Get all tasks in the proposal list with a specific status
   */
  async getTasksByStatus(status: string): Promise<ClickUpTask[]> {
    const response = await this.client.get(`/list/${this.listId}/task`, {
      params: {
        statuses: [status],
        include_closed: false,
      },
    });
    return response.data.tasks;
  }

  /**
   * Update the status of a task
   */
  async updateTaskStatus(taskId: string, status: string): Promise<void> {
    await this.client.put(`/task/${taskId}`, {
      status,
    });
  }

  /**
   * Set a custom field value on a task
   */
  async setCustomFieldValue(
    taskId: string,
    fieldId: string,
    value: unknown
  ): Promise<void> {
    await this.client.post(`/task/${taskId}/field/${fieldId}`, {
      value,
    });
  }

  /**
   * Add a comment to a task
   */
  async addComment(taskId: string, comment: ClickUpComment): Promise<void> {
    await this.client.post(`/task/${taskId}/comment`, comment);
  }

  /**
   * Set the assignee of a task
   */
  async setAssignee(taskId: string, assigneeId: number): Promise<void> {
    await this.client.put(`/task/${taskId}`, {
      assignees: {
        add: [assigneeId],
      },
    });
  }

  /**
   * Get custom fields for the list (to discover field IDs)
   */
  async getListCustomFields(): Promise<ClickUpCustomField[]> {
    const response = await this.client.get(`/list/${this.listId}/field`);
    return response.data.fields;
  }

  /**
   * Create a webhook for the workspace
   */
  async createWebhook(
    endpoint: string,
    events: string[]
  ): Promise<{ id: string; webhook: unknown }> {
    const response = await this.client.post(
      `/team/${this.workspaceId}/webhook`,
      {
        endpoint,
        events,
      }
    );
    return response.data;
  }

  /**
   * Delete a webhook
   */
  async deleteWebhook(webhookId: string): Promise<void> {
    await this.client.delete(`/webhook/${webhookId}`);
  }
}
