/**
 * zukunvt Team Assignments for Proposals
 */

export interface TeamMember {
  name: string;
  role: string;
}

export interface TeamDepartment {
  lead: TeamMember;
  team: TeamMember[];
  description: string;
}

export const TEAM_ASSIGNMENTS: Record<string, TeamDepartment> = {
  strategy: {
    lead: { name: 'Moritz Gruber', role: 'Head of Strategy' },
    team: [
      { name: 'Viktor Matic', role: 'CEO & Strategy' },
      { name: 'Bartholomäus Traubeck', role: 'Strategy & Creative' },
      { name: 'Arno Parmeggiani', role: 'Strategy & Marketing' },
    ],
    description: 'Strategische Führung und Business Consulting',
  },

  branding: {
    lead: { name: 'Bartholomäus Traubeck', role: 'Creative Direction' },
    team: [
      { name: 'Stephanie Innerbichler', role: 'Design' },
      { name: 'Miriam Tessadri', role: 'Design' },
      { name: 'Linsey Dolleman', role: 'Digital Design' },
    ],
    description: 'Kreative Umsetzung und Brand Development',
  },

  marketing: {
    lead: { name: 'Arno Parmeggiani', role: 'Head of Marketing' },
    team: [
      { name: 'Silvia Bucciol', role: 'Digital Marketing' },
      { name: 'Domenico Nunziata', role: 'Content & Copy' },
      { name: 'Lorenzo Gabardi', role: 'Digital Marketing' },
    ],
    description: 'Marketing-Aktivierung und Performance',
  },

  projectManagement: {
    lead: { name: 'Johanna Pichler', role: 'COO' },
    team: [
      { name: 'Kristina Unterthurner', role: 'Strategy & PM' },
      { name: 'Giulia Cestaro', role: 'Project Manager' },
    ],
    description: 'Persönliche Betreuung und Projektkoordination',
  },
};

export type ServiceType =
  | 'Strategy Foundation'
  | 'Brand Transformation'
  | 'Agile Activation'
  | 'Content Engine'
  | 'Digital Growth'
  | 'Full-Service Partner'
  | 'Employer Branding'
  | 'AI Audit'
  | 'AI Setup'
  | 'Custom';

/**
 * Map services to required team departments
 */
export const SERVICE_TEAM_MAPPING: Record<ServiceType, string[]> = {
  'Strategy Foundation': ['strategy', 'projectManagement'],
  'Brand Transformation': ['strategy', 'branding', 'projectManagement'],
  'Agile Activation': ['strategy', 'marketing', 'projectManagement'],
  'Content Engine': ['marketing', 'branding', 'projectManagement'],
  'Digital Growth': ['marketing', 'projectManagement'],
  'Full-Service Partner': ['strategy', 'branding', 'marketing', 'projectManagement'],
  'Employer Branding': ['strategy', 'branding', 'marketing', 'projectManagement'],
  'AI Audit': ['strategy', 'projectManagement'],
  'AI Setup': ['strategy', 'marketing', 'projectManagement'],
  'Custom': ['strategy', 'projectManagement'],
};

/**
 * Get team members assigned to a set of services
 */
export function getTeamForServices(services: ServiceType[]): TeamDepartment[] {
  const departmentKeys = new Set<string>();
  for (const service of services) {
    const departments = SERVICE_TEAM_MAPPING[service] ?? ['strategy', 'projectManagement'];
    departments.forEach((d) => departmentKeys.add(d));
  }

  return Array.from(departmentKeys)
    .map((key) => TEAM_ASSIGNMENTS[key])
    .filter(Boolean);
}

/**
 * Generate team paragraph for proposals
 */
export function generateTeamParagraph(services: ServiceType[], language: 'DE' | 'IT' | 'EN'): string {
  const departments = getTeamForServices(services);

  if (language === 'DE') {
    const parts = departments.map((dept) => {
      const members = [dept.lead, ...dept.team.slice(0, 1)]
        .map((m) => m.name)
        .join('/');
      return `${dept.description} (${members})`;
    });
    return `Ihr Projekt wird von einem integrierten Team betreut: ${parts.join(', ')}.`;
  }

  if (language === 'IT') {
    const parts = departments.map((dept) => {
      const members = [dept.lead, ...dept.team.slice(0, 1)]
        .map((m) => m.name)
        .join('/');
      return `${dept.description} (${members})`;
    });
    return `Il vostro progetto sarà seguito da un team integrato: ${parts.join(', ')}.`;
  }

  // EN
  const parts = departments.map((dept) => {
    const members = [dept.lead, ...dept.team.slice(0, 1)]
      .map((m) => m.name)
      .join('/');
    return `${dept.description} (${members})`;
  });
  return `Your project will be managed by an integrated team: ${parts.join(', ')}.`;
}
