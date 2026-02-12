/**
 * Google Drive Client
 * Reads template files and reference proposals from the shared Drive folder
 */

import { google, drive_v3 } from 'googleapis';
import { GoogleAuth } from 'googleapis-common';
import fs from 'fs';
import path from 'path';

export interface DriveFile {
  id: string;
  name: string;
  mimeType: string;
  modifiedTime: string;
  webViewLink: string;
}

export class GoogleDriveClient {
  private drive: drive_v3.Drive;
  private folderId: string;

  constructor(config: {
    serviceAccountKeyPath: string;
    folderId: string;
  }) {
    this.folderId = config.folderId;

    const keyFile = path.resolve(config.serviceAccountKeyPath);
    const auth = new google.auth.GoogleAuth({
      keyFile,
      scopes: [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.file',
      ],
    });

    this.drive = google.drive({ version: 'v3', auth: auth as GoogleAuth });
  }

  /**
   * List all files in the template folder
   */
  async listTemplateFiles(): Promise<DriveFile[]> {
    const response = await this.drive.files.list({
      q: `'${this.folderId}' in parents and trashed = false`,
      fields: 'files(id, name, mimeType, modifiedTime, webViewLink)',
      orderBy: 'modifiedTime desc',
      pageSize: 50,
    });

    return (response.data.files ?? []).map((f) => ({
      id: f.id!,
      name: f.name!,
      mimeType: f.mimeType!,
      modifiedTime: f.modifiedTime!,
      webViewLink: f.webViewLink!,
    }));
  }

  /**
   * List files in a subfolder by name
   */
  async listFilesInSubfolder(subfolderName: string): Promise<DriveFile[]> {
    // First, find the subfolder
    const folderResponse = await this.drive.files.list({
      q: `'${this.folderId}' in parents and name = '${subfolderName}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false`,
      fields: 'files(id, name)',
    });

    const subfolder = folderResponse.data.files?.[0];
    if (!subfolder) return [];

    // Then list files in the subfolder
    const filesResponse = await this.drive.files.list({
      q: `'${subfolder.id}' in parents and trashed = false`,
      fields: 'files(id, name, mimeType, modifiedTime, webViewLink)',
      orderBy: 'modifiedTime desc',
      pageSize: 20,
    });

    return (filesResponse.data.files ?? []).map((f) => ({
      id: f.id!,
      name: f.name!,
      mimeType: f.mimeType!,
      modifiedTime: f.modifiedTime!,
      webViewLink: f.webViewLink!,
    }));
  }

  /**
   * Get the content of a Google Doc as plain text
   */
  async getDocContent(fileId: string): Promise<string> {
    const response = await this.drive.files.export({
      fileId,
      mimeType: 'text/plain',
    });
    return response.data as string;
  }

  /**
   * Get the content of a Google Doc as HTML
   */
  async getDocAsHtml(fileId: string): Promise<string> {
    const response = await this.drive.files.export({
      fileId,
      mimeType: 'text/html',
    });
    return response.data as string;
  }

  /**
   * Load reference proposals for a given language
   */
  async loadReferenceProposals(language: string): Promise<Array<{ name: string; content: string }>> {
    const files = await this.listFilesInSubfolder('Referenz-Angebote');

    // Filter by language suffix and Google Docs type
    const relevantFiles = files.filter(
      (f) =>
        f.mimeType === 'application/vnd.google-apps.document' &&
        (f.name.includes(`_${language}`) || f.name.includes(`_${language.toLowerCase()}`))
    );

    // Load up to 3 reference proposals
    const proposals: Array<{ name: string; content: string }> = [];
    for (const file of relevantFiles.slice(0, 3)) {
      try {
        const content = await this.getDocContent(file.id);
        proposals.push({ name: file.name, content });
      } catch (error) {
        console.warn(`Could not load reference proposal "${file.name}":`, error);
      }
    }

    return proposals;
  }

  /**
   * Move a file to a specific subfolder within the main folder
   */
  async moveToSubfolder(fileId: string, subfolderName: string): Promise<void> {
    // Find or create the subfolder
    const folderResponse = await this.drive.files.list({
      q: `'${this.folderId}' in parents and name = '${subfolderName}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false`,
      fields: 'files(id)',
    });

    let subfolderId: string;
    if (folderResponse.data.files?.length) {
      subfolderId = folderResponse.data.files[0].id!;
    } else {
      const created = await this.drive.files.create({
        requestBody: {
          name: subfolderName,
          mimeType: 'application/vnd.google-apps.folder',
          parents: [this.folderId],
        },
        fields: 'id',
      });
      subfolderId = created.data.id!;
    }

    // Move the file
    await this.drive.files.update({
      fileId,
      addParents: subfolderId,
      removeParents: this.folderId,
      fields: 'id, parents',
    });
  }
}
