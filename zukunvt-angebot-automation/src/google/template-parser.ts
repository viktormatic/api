/**
 * Template Parser
 * Parses existing proposals from Google Drive to extract structure and formatting patterns
 */

export interface ParsedTemplate {
  sections: ParsedSection[];
  formatting: FormattingPattern;
  language: string;
}

export interface ParsedSection {
  title: string;
  content: string;
  type: 'cover_letter' | 'legal_notice' | 'calculation' | 'summary' | 'references' | 'unknown';
}

export interface FormattingPattern {
  hasTable: boolean;
  hasPageBreaks: boolean;
  estimatedPages: number;
}

/**
 * Section detection keywords per language
 */
const SECTION_KEYWORDS: Record<string, Record<string, string[]>> = {
  DE: {
    cover_letter: ['anschreiben', 'sehr geehrte', 'liebe', 'freue mich'],
    legal_notice: ['rechtlich', 'agb', 'gültigkeit', 'urheberrecht'],
    calculation: ['kalkulation', 'preis', 'phase', 'leistung'],
    summary: ['zusammenfassung', 'zahlungsbedingungen', 'netto', 'brutto', 'mwst'],
    references: ['referenz', 'partner', 'testimonial'],
  },
  IT: {
    cover_letter: ['presentazione', 'gentile', 'caro', 'piacere'],
    legal_notice: ['legale', 'condizioni', 'validità', 'diritti'],
    calculation: ['calcolo', 'prezzo', 'fase', 'servizio'],
    summary: ['riepilogo', 'pagamento', 'netto', 'lordo', 'iva'],
    references: ['referenze', 'partner', 'testimonianza'],
  },
  EN: {
    cover_letter: ['cover', 'dear', 'pleased', 'proposal'],
    legal_notice: ['legal', 'terms', 'validity', 'copyright'],
    calculation: ['calculation', 'price', 'phase', 'service'],
    summary: ['summary', 'payment', 'net', 'gross', 'vat'],
    references: ['reference', 'partner', 'testimonial'],
  },
};

/**
 * Parse a raw proposal text into structured sections
 */
export function parseProposalText(text: string, language: string = 'DE'): ParsedTemplate {
  const lang = language.toUpperCase();
  const keywords = SECTION_KEYWORDS[lang] ?? SECTION_KEYWORDS.DE;

  // Split by likely page breaks or section dividers
  const rawSections = text
    .split(/(?:\r?\n){3,}|(?:---+)|(?:===+)/)
    .filter((s) => s.trim().length > 0);

  const sections: ParsedSection[] = rawSections.map((raw) => {
    const content = raw.trim();
    const type = detectSectionType(content.toLowerCase(), keywords);
    const title = extractTitle(content);
    return { title, content, type };
  });

  const formatting: FormattingPattern = {
    hasTable: text.includes('|') && text.includes('---'),
    hasPageBreaks: rawSections.length >= 4,
    estimatedPages: Math.max(rawSections.length, 5),
  };

  return { sections, formatting, language: lang };
}

/**
 * Detect the section type based on content keywords
 */
function detectSectionType(
  content: string,
  keywords: Record<string, string[]>
): ParsedSection['type'] {
  let bestMatch: ParsedSection['type'] = 'unknown';
  let bestScore = 0;

  for (const [type, words] of Object.entries(keywords)) {
    const score = words.filter((w) => content.includes(w)).length;
    if (score > bestScore) {
      bestScore = score;
      bestMatch = type as ParsedSection['type'];
    }
  }

  return bestMatch;
}

/**
 * Extract the first line as a title
 */
function extractTitle(content: string): string {
  const firstLine = content.split('\n')[0].trim();
  // Remove common formatting characters
  return firstLine.replace(/^[#*_\-=]+\s*/, '').trim();
}

/**
 * Extract pricing information from a calculation section
 */
export function extractPricingFromTemplate(
  section: ParsedSection
): Array<{ item: string; price: number }> {
  const items: Array<{ item: string; price: number }> = [];
  const lines = section.content.split('\n');

  for (const line of lines) {
    // Match patterns like "€1.500" or "€ 1,500.00" or "EUR 3.500"
    const priceMatch = line.match(/(?:€|EUR)\s*([\d.,]+)/i);
    if (priceMatch) {
      const priceStr = priceMatch[1].replace(/\./g, '').replace(',', '.');
      const price = parseFloat(priceStr);
      if (!isNaN(price)) {
        // Use the text before the price as the item name
        const item = line.substring(0, line.indexOf(priceMatch[0])).trim();
        items.push({ item: item || 'Item', price });
      }
    }
  }

  return items;
}

/**
 * Generate a context summary from parsed templates for AI prompt
 */
export function generateTemplateContext(templates: ParsedTemplate[]): string {
  if (templates.length === 0) {
    return 'Keine Referenz-Templates verfügbar. Verwende die zukunvt-Standardstruktur.';
  }

  const summaries = templates.map((t, i) => {
    const sectionTypes = t.sections
      .map((s) => s.type)
      .filter((type) => type !== 'unknown');
    return `Template ${i + 1}: ${t.sections.length} Sektionen (${sectionTypes.join(', ')}), Sprache: ${t.language}`;
  });

  return `Referenz-Templates:\n${summaries.join('\n')}`;
}
