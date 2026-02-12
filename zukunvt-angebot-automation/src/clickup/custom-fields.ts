/**
 * ClickUp Custom Field Mapping
 * Maps custom field names to their IDs and parses values
 */

import { ClickUpCustomField } from './client';
import { AngebotTaskData, Language, BudgetRange, Timeline, Industry } from '../models/client-data';
import { ServiceType } from '../config/team';

/**
 * Custom field name constants — must match ClickUp field names exactly
 */
export const FIELD_NAMES = {
  KUNDEN_NAME: 'Kundenname',
  ANSPRECHPARTNER: 'Ansprechpartner',
  EMAIL: 'E-Mail',
  SERVICES: 'Services',
  BRANCHE: 'Branche',
  PROJEKT_BESCHREIBUNG: 'Projektbeschreibung',
  BUDGET: 'Budget',
  TIMELINE: 'Timeline',
  SPRACHE: 'Sprache',
  BESTEHENDER_KUNDE: 'Bestandskunde',
  NOTIZEN: 'Notizen',
  ANGEBOT_LINK: 'Angebot Link',
} as const;

/**
 * Cached field ID map (populated from ClickUp API)
 */
let fieldIdMap: Map<string, string> | null = null;

/**
 * Build a field name → field ID lookup from list custom fields
 */
export function buildFieldIdMap(fields: ClickUpCustomField[]): Map<string, string> {
  const map = new Map<string, string>();
  for (const field of fields) {
    map.set(field.name, field.id);
  }
  fieldIdMap = map;
  return map;
}

/**
 * Get a field ID by its display name
 */
export function getFieldId(fieldName: string): string | undefined {
  return fieldIdMap?.get(fieldName);
}

/**
 * Extract a custom field value by name from a task's custom fields array
 */
function getFieldValue(
  customFields: ClickUpCustomField[],
  fieldName: string
): unknown {
  const field = customFields.find((f) => f.name === fieldName);
  return field?.value ?? null;
}

/**
 * Parse a multi-select (labels) field into a ServiceType array
 */
function parseServicesField(value: unknown): ServiceType[] {
  if (!Array.isArray(value)) return [];
  // ClickUp labels fields return array of option IDs or label objects
  return value
    .map((item: unknown) => {
      if (typeof item === 'string') return item as ServiceType;
      if (typeof item === 'object' && item !== null && 'label' in item) {
        return (item as { label: string }).label as ServiceType;
      }
      return null;
    })
    .filter((s): s is ServiceType => s !== null);
}

/**
 * Parse ClickUp custom fields into typed AngebotTaskData
 */
export function parseTaskData(
  taskId: string,
  taskName: string,
  customFields: ClickUpCustomField[]
): AngebotTaskData {
  const kundenName = getFieldValue(customFields, FIELD_NAMES.KUNDEN_NAME);
  const ansprechpartner = getFieldValue(customFields, FIELD_NAMES.ANSPRECHPARTNER);
  const email = getFieldValue(customFields, FIELD_NAMES.EMAIL);
  const services = getFieldValue(customFields, FIELD_NAMES.SERVICES);
  const branche = getFieldValue(customFields, FIELD_NAMES.BRANCHE);
  const projektBeschreibung = getFieldValue(customFields, FIELD_NAMES.PROJEKT_BESCHREIBUNG);
  const budget = getFieldValue(customFields, FIELD_NAMES.BUDGET);
  const timeline = getFieldValue(customFields, FIELD_NAMES.TIMELINE);
  const sprache = getFieldValue(customFields, FIELD_NAMES.SPRACHE);
  const bestehenderKunde = getFieldValue(customFields, FIELD_NAMES.BESTEHENDER_KUNDE);
  const notizen = getFieldValue(customFields, FIELD_NAMES.NOTIZEN);

  return {
    taskId,
    taskName,
    kundenName: (kundenName as string) ?? taskName,
    ansprechpartner: (ansprechpartner as string) ?? '',
    email: (email as string) ?? '',
    services: parseServicesField(services),
    branche: (branche as Industry) ?? 'Other',
    projektBeschreibung: (projektBeschreibung as string) ?? '',
    budget: (budget as BudgetRange) ?? '10-20k',
    timeline: (timeline as Timeline) ?? '3-6 Monate',
    sprache: (sprache as Language) ?? 'DE',
    bestehenderKunde: bestehenderKunde === true || bestehenderKunde === 'true',
    notizen: (notizen as string) ?? '',
  };
}
