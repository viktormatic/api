/**
 * Google Docs Client
 * Creates and formats proposal documents programmatically
 */

import { google, docs_v1 } from 'googleapis';
import { GoogleAuth } from 'googleapis-common';
import path from 'path';
import { Proposal } from '../models/proposal';
import { DOC_FORMATTING } from '../config/templates';

export class GoogleDocsClient {
  private docs: docs_v1.Docs;
  private driveService: ReturnType<typeof google.drive>;
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
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/drive.file',
      ],
    });

    this.docs = google.docs({ version: 'v1', auth: auth as GoogleAuth });
    this.driveService = google.drive({ version: 'v3', auth: auth as GoogleAuth });
  }

  /**
   * Create a new Google Doc with the proposal content
   */
  async createProposalDoc(proposal: Proposal, title: string): Promise<{
    docId: string;
    docUrl: string;
  }> {
    // Create the document in the target folder
    const fileResponse = await this.driveService.files.create({
      requestBody: {
        name: title,
        mimeType: 'application/vnd.google-apps.document',
        parents: [this.folderId],
      },
      fields: 'id, webViewLink',
    });

    const docId = fileResponse.data.id!;
    const docUrl = fileResponse.data.webViewLink!;

    // Build all the content requests
    const requests = this.buildDocumentRequests(proposal);

    // Apply content and formatting
    if (requests.length > 0) {
      await this.docs.documents.batchUpdate({
        documentId: docId,
        requestBody: { requests },
      });
    }

    return { docId, docUrl };
  }

  /**
   * Build Google Docs API requests for the full proposal
   */
  private buildDocumentRequests(proposal: Proposal): docs_v1.Schema$Request[] {
    const requests: docs_v1.Schema$Request[] = [];
    let currentIndex = 1; // Google Docs index starts at 1

    // Helper: insert text and advance index
    const insertText = (text: string): number => {
      requests.push({
        insertText: {
          location: { index: currentIndex },
          text,
        },
      });
      const startIndex = currentIndex;
      currentIndex += text.length;
      return startIndex;
    };

    // Helper: format a range as heading
    const formatHeading = (start: number, end: number, level: 'HEADING_1' | 'HEADING_2'): void => {
      requests.push({
        updateParagraphStyle: {
          range: { startIndex: start, endIndex: end },
          paragraphStyle: {
            namedStyleType: level,
          },
          fields: 'namedStyleType',
        },
      });
    };

    // Helper: format text style
    const formatText = (start: number, end: number, bold?: boolean, fontSize?: number, color?: string): void => {
      const textStyle: docs_v1.Schema$TextStyle = {};
      const fields: string[] = [];

      if (bold !== undefined) {
        textStyle.bold = bold;
        fields.push('bold');
      }
      if (fontSize !== undefined) {
        textStyle.fontSize = { magnitude: fontSize, unit: 'PT' };
        fields.push('fontSize');
      }
      if (color) {
        const r = parseInt(color.slice(1, 3), 16) / 255;
        const g = parseInt(color.slice(3, 5), 16) / 255;
        const b = parseInt(color.slice(5, 7), 16) / 255;
        textStyle.foregroundColor = {
          color: { rgbColor: { red: r, green: g, blue: b } },
        };
        fields.push('foregroundColor');
      }

      if (fields.length > 0) {
        requests.push({
          updateTextStyle: {
            range: { startIndex: start, endIndex: end },
            textStyle,
            fields: fields.join(','),
          },
        });
      }
    };

    // --- Page 1: Cover Letter ---
    const coverTitle = proposal.coverLetter.greeting + '\n';
    const coverStart = insertText(coverTitle);
    formatHeading(coverStart, currentIndex, 'HEADING_1');

    insertText(proposal.coverLetter.body + '\n\n');
    insertText(proposal.coverLetter.teamParagraph + '\n\n');
    insertText(proposal.coverLetter.closing + '\n');

    // Page break
    requests.push({
      insertPageBreak: { location: { index: currentIndex } },
    });
    currentIndex += 1;

    // --- Page 2: Legal Notice ---
    const legalTitle = this.getSectionTitle(proposal.language, 'legal_notice') + '\n';
    const legalStart = insertText(legalTitle);
    formatHeading(legalStart, currentIndex, 'HEADING_1');

    insertText(proposal.legalNotice.validity + '\n\n');
    insertText(proposal.legalNotice.copyright + '\n\n');
    insertText(proposal.legalNotice.costOverrun + '\n\n');
    insertText(proposal.legalNotice.agb + '\n');

    // Page break
    requests.push({
      insertPageBreak: { location: { index: currentIndex } },
    });
    currentIndex += 1;

    // --- Page 3: Calculation ---
    const calcTitle = this.getSectionTitle(proposal.language, 'calculation') + '\n';
    const calcStart = insertText(calcTitle);
    formatHeading(calcStart, currentIndex, 'HEADING_1');

    for (const row of proposal.calculation.rows) {
      // Phase heading
      const phaseTitle = `${row.nr}. ${row.title}\n`;
      const phaseStart = insertText(phaseTitle);
      formatHeading(phaseStart, currentIndex, 'HEADING_2');
      formatText(phaseStart, currentIndex, true, undefined, DOC_FORMATTING.colors.primary);

      // Price
      const priceText = `Preis: €${row.price.toLocaleString('de-DE')}\n\n`;
      const priceStart = insertText(priceText);
      formatText(priceStart, currentIndex, true);

      // Details
      if (row.details.fokuspunkte.length > 0) {
        const fpLabel = insertText('Fokuspunkte: ');
        formatText(fpLabel, currentIndex, true);
        insertText(row.details.fokuspunkte.join(', ') + '\n');
      }

      if (row.details.inhalt.length > 0) {
        const inhLabel = insertText('Inhalt: ');
        formatText(inhLabel, currentIndex, true);
        insertText(row.details.inhalt.join(', ') + '\n');
      }

      if (row.details.phasenziel) {
        const pzLabel = insertText('Phasenziel: ');
        formatText(pzLabel, currentIndex, true);
        insertText(row.details.phasenziel + '\n');
      }

      if (row.details.output.length > 0) {
        const outLabel = insertText('Output: ');
        formatText(outLabel, currentIndex, true);
        insertText(row.details.output.join(', ') + '\n');
      }

      insertText('\n');
    }

    // Page break
    requests.push({
      insertPageBreak: { location: { index: currentIndex } },
    });
    currentIndex += 1;

    // --- Page 4: Summary ---
    const summaryTitle = this.getSectionTitle(proposal.language, 'summary') + '\n';
    const summaryStart = insertText(summaryTitle);
    formatHeading(summaryStart, currentIndex, 'HEADING_1');

    // Financial summary
    const { financials } = proposal.summary;
    const netLabel = insertText('Netto: ');
    formatText(netLabel, currentIndex, true);
    insertText(`€${financials.netTotal.toLocaleString('de-DE')}\n`);

    const vatLabel = insertText(`MwSt. (${(financials.vatRate * 100).toFixed(0)}%): `);
    formatText(vatLabel, currentIndex, true);
    insertText(`€${financials.vatAmount.toLocaleString('de-DE')}\n`);

    const grossLabel = insertText('Brutto: ');
    formatText(grossLabel, currentIndex, true);
    insertText(`€${financials.grossTotal.toLocaleString('de-DE')}\n\n`);

    // Payment terms
    const ptTitle = insertText('Zahlungsbedingungen\n');
    formatHeading(ptTitle, currentIndex, 'HEADING_2');

    for (const term of proposal.summary.paymentTerms) {
      insertText(`• ${term.percentage}% (€${term.amount.toLocaleString('de-DE')}): ${term.label}\n`);
    }
    insertText('\n');

    // Signature section
    insertText(proposal.summary.signatureSection.agreementText + '\n\n');
    insertText(`${proposal.summary.signatureSection.agencyName}: ____________________\n\n`);
    insertText(`${proposal.summary.signatureSection.partnerName}: ____________________\n\n`);
    insertText('Datum: ________________  Ort: ________________\n');

    // Page break
    requests.push({
      insertPageBreak: { location: { index: currentIndex } },
    });
    currentIndex += 1;

    // --- Page 5: References ---
    const refTitle = this.getSectionTitle(proposal.language, 'references') + '\n';
    const refStart = insertText(refTitle);
    formatHeading(refStart, currentIndex, 'HEADING_1');

    for (const ref of proposal.references.entries) {
      const refNameStart = insertText(`${ref.partnerName} — ${ref.industry}\n`);
      formatText(refNameStart, currentIndex, true);
      insertText(`${ref.description}\n`);
      if (ref.testimonial) {
        insertText(`"${ref.testimonial}"\n`);
      }
      insertText('\n');
    }

    insertText(`\n${proposal.references.portfolioLink}\n`);

    // Apply global font
    requests.push({
      updateTextStyle: {
        range: { startIndex: 1, endIndex: currentIndex },
        textStyle: {
          weightedFontFamily: {
            fontFamily: DOC_FORMATTING.font,
          },
        },
        fields: 'weightedFontFamily',
      },
    });

    return requests;
  }

  /**
   * Get localized section title
   */
  private getSectionTitle(
    language: 'DE' | 'IT' | 'EN',
    sectionId: string
  ): string {
    const titles: Record<string, Record<string, string>> = {
      legal_notice: {
        DE: 'Rechtlicher Hinweis',
        IT: 'Avviso Legale',
        EN: 'Legal Notice',
      },
      calculation: {
        DE: 'Kalkulation',
        IT: 'Calcolo',
        EN: 'Calculation',
      },
      summary: {
        DE: 'Zusammenfassung & Konditionen',
        IT: 'Riepilogo e Condizioni',
        EN: 'Summary & Terms',
      },
      references: {
        DE: 'Partner-Referenzen',
        IT: 'Referenze Partner',
        EN: 'Partner References',
      },
    };
    return titles[sectionId]?.[language] ?? sectionId;
  }
}
