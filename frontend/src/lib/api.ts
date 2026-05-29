import { createClient } from './supabase';

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

async function authHeaders(): Promise<HeadersInit> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error('Non authentifié');
  return { Authorization: `Bearer ${token}` };
}

// Pour multipart/form-data : NE PAS mettre Content-Type (le browser le génère avec boundary)
async function authHeadersNoContent(): Promise<HeadersInit> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error('Non authentifié');
  return { Authorization: `Bearer ${token}` };
}

// Erreur API enrichie : code HTTP + message technique + message humain
export class ApiError extends Error {
  status: number;
  detail: string;
  userMessage: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.userMessage = humanizeError(status, detail);
  }
}

// Traduit un statut/détail technique en message clair pour l'ingénieur
function humanizeError(status: number, detail: string): string {
  const d = (detail || '').toLowerCase();
  if (d.includes('quota')) return detail; // message quota déjà explicite
  switch (status) {
    case 400: return detail || 'La demande est incomplète ou invalide.';
    case 401: return 'Votre session a expiré. Reconnectez-vous pour continuer.';
    case 403: return detail || "Vous n'avez pas les droits pour cette action.";
    case 404: return "L'élément demandé est introuvable. Il a peut-être été supprimé.";
    case 409: return detail || 'Conflit : cette action entre en conflit avec un état existant.';
    case 413: return 'Le fichier est trop volumineux.';
    case 422: return detail || 'Certaines données sont mal renseignées.';
    case 429: return 'Trop de requêtes. Patientez un instant avant de réessayer.';
    case 500:
    case 502:
    case 503:
      return 'Une erreur technique est survenue de notre côté. Réessayez dans un instant.';
    default:
      return detail || 'Une erreur est survenue. Réessayez.';
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Auth / Me
  me: async () => {
    const res = await fetch(`${API_URL}/api/auth/me`, { headers: await authHeaders() });
    return handle<any>(res);
  },
  inviteUser: async (email: string, role: 'admin' | 'member' | 'viewer') => {
    const res = await fetch(`${API_URL}/api/auth/invite`, {
      method: 'POST',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, role }),
    });
    return handle<any>(res);
  },
  deleteAccount: async () => {
    const res = await fetch(`${API_URL}/api/auth/me`, { method: 'DELETE', headers: await authHeaders() });
    return handle<any>(res);
  },
  exportData: async () => {
    const res = await fetch(`${API_URL}/api/auth/export`, { headers: await authHeaders() });
    return handle<any>(res);
  },

  // Projects
  listProjects: async (archived = false) => {
    const res = await fetch(`${API_URL}/api/projects?archived=${archived}`, { headers: await authHeaders() });
    return handle<{ projects: any[] }>(res);
  },
  getProject: async (id: string) => {
    const res = await fetch(`${API_URL}/api/projects/${id}`, { headers: await authHeaders() });
    return handle<any>(res);
  },
  createProject: async (data: any) => {
    const res = await fetch(`${API_URL}/api/projects`, {
      method: 'POST',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handle<any>(res);
  },
  updateProject: async (id: string, data: any) => {
    const res = await fetch(`${API_URL}/api/projects/${id}`, {
      method: 'PATCH',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handle<any>(res);
  },
  deleteProject: async (id: string) => {
    const res = await fetch(`${API_URL}/api/projects/${id}`, { method: 'DELETE', headers: await authHeaders() });
    return handle<void>(res);
  },

  // Namespace projects (alias moderne)
  projects: {
    list: async (archived = false) => {
      const res = await fetch(`${API_URL}/api/projects?archived=${archived}`, { headers: await authHeaders() });
      return handle<{ projects: any[] }>(res);
    },
    get: async (id: string) => {
      const res = await fetch(`${API_URL}/api/projects/${id}`, { headers: await authHeaders() });
      return handle<any>(res);
    },
    create: async (data: any) => {
      const res = await fetch(`${API_URL}/api/projects`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return handle<any>(res);
    },
  },

  listProjectDocuments: async (id: string) => {
    const res = await fetch(`${API_URL}/api/projects/${id}/documents`, { headers: await authHeaders() });
    return handle<{ documents: any[] }>(res);
  },
  listProjectTasks: async (id: string) => {
    const res = await fetch(`${API_URL}/api/projects/${id}/tasks`, { headers: await authHeaders() });
    return handle<{ tasks: any[] }>(res);
  },

  // Documents
  uploadDocument: async (file: File, projectId?: string, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append('file', file);
    if (projectId) form.append('project_id', projectId);

    const headers = await authHeaders();
    return new Promise<any>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_URL}/api/documents/upload`);
      Object.entries(headers).forEach(([k, v]) => xhr.setRequestHeader(k, v as string));
      if (onProgress) {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
        };
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try { resolve(JSON.parse(xhr.responseText)); } catch { resolve({}); }
        } else {
          try { reject(new Error(JSON.parse(xhr.responseText).detail || `HTTP ${xhr.status}`)); }
          catch { reject(new Error(`HTTP ${xhr.status}`)); }
        }
      };
      xhr.onerror = () => reject(new Error('Erreur réseau'));
      xhr.send(form);
    });
  },
  listDocuments: async (projectId?: string) => {
    const q = projectId ? `?project_id=${projectId}` : '';
    const res = await fetch(`${API_URL}/api/documents${q}`, { headers: await authHeaders() });
    return handle<{ documents: any[] }>(res);
  },
  getDocument: async (id: string) => {
    const res = await fetch(`${API_URL}/api/documents/${id}`, { headers: await authHeaders() });
    return handle<any>(res);
  },
  deleteDocument: async (id: string) => {
    const res = await fetch(`${API_URL}/api/documents/${id}`, { method: 'DELETE', headers: await authHeaders() });
    return handle<void>(res);
  },

  // Tasks
  createTask: async (data: any) => {
    const res = await fetch(`${API_URL}/api/tasks`, {
      method: 'POST',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handle<any>(res);
  },
  listTasks: async (params?: { project_id?: string; status?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.project_id) qs.set('project_id', params.project_id);
    if (params?.status) qs.set('status', params.status);
    if (params?.limit) qs.set('limit', String(params.limit));
    const res = await fetch(`${API_URL}/api/tasks?${qs}`, { headers: await authHeaders() });
    return handle<{ tasks: any[] }>(res);
  },
  getTask: async (id: string) => {
    const res = await fetch(`${API_URL}/api/tasks/${id}`, { headers: await authHeaders() });
    return handle<any>(res);
  },
  getTaskStatus: async (id: string) => {
    const res = await fetch(`${API_URL}/api/tasks/${id}/status`, { headers: await authHeaders() });
    return handle<{ id: string; status: string; progress: number; result_url?: string; result_preview?: string; error_message?: string }>(res);
  },
  retryTask: async (id: string) => {
    const res = await fetch(`${API_URL}/api/tasks/${id}/retry`, { method: 'POST', headers: await authHeaders() });
    return handle<any>(res);
  },

  // V5 — Régénération intelligente
  regenerateTask: async (id: string, body: {
    reasons: string[];
    custom_feedback?: string;
    target_sections?: string[];
    upgrade_model?: boolean;
  }) => {
    const res = await fetch(`${API_URL}/api/tasks/${id}/regenerate`, {
      method: 'POST',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return handle<{
      status: string; task_id: string;
      attempt: number; remaining_regenerations: number;
    }>(res);
  },
  getRegenerations: async (id: string) => {
    const res = await fetch(`${API_URL}/api/tasks/${id}/regenerations`, { headers: await authHeaders() });
    return handle<{
      count: number; max_per_task: number; last_at?: string;
      history: any[]; remaining: number;
    }>(res);
  },

  // Validation assistée (Leviers 1-4)
  getTaskReview: async (id: string) => {
    const res = await fetch(`${API_URL}/api/tasks/${id}/review`, { headers: await authHeaders() });
    return handle<{
      task_id: string; confidence_score: number; confidence_level: string;
      ready_to_approve: boolean; alerts: string[]; failed_checks: any[];
      summary: string; nb_points_to_verify: number;
      can_approve: boolean; approval_reason: string; review_status: string;
    }>(res);
  },
  approveTask: async (id: string, note?: string) => {
    const res = await fetch(`${API_URL}/api/tasks/${id}/approve`, {
      method: 'POST',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: note || '', channel: 'web' }),
    });
    return handle<{ task_id: string; review_status: string; reason: string }>(res);
  },
  rejectTask: async (id: string, note?: string) => {
    const res = await fetch(`${API_URL}/api/tasks/${id}/reject`, {
      method: 'POST',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: note || '', channel: 'web' }),
    });
    return handle<{ task_id: string; review_status: string; reason: string }>(res);
  },
  getReviewQueue: async () => {
    const res = await fetch(`${API_URL}/api/tasks/review/queue`, { headers: await authHeaders() });
    return handle<{
      queue: any[];
      counts: { ready_to_approve: number; pending_review: number; needs_revision: number };
    }>(res);
  },

  // Parcours d'affaire (journey)
  getProjectJourney: async (projectId: string) => {
    const res = await fetch(`${API_URL}/api/projects/${projectId}/journey`, { headers: await authHeaders() });
    return handle<{
      phases: any[]; global_progress: number;
      next_recommended: any; current_phase: string;
    }>(res);
  },
  setProjectPhase: async (projectId: string, phase: string) => {
    const res = await fetch(`${API_URL}/api/projects/${projectId}/phase`, {
      method: 'PATCH',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_phase: phase }),
    });
    return handle<any>(res);
  },
  exportDossierUrl: (projectId: string, onlyApproved = true) =>
    `${API_URL}/api/projects/${projectId}/export-dossier?only_approved=${onlyApproved}`,

  // Dashboard ingénieur + analytics + notifications
  engineerDashboard: async () => {
    const res = await fetch(`${API_URL}/api/dashboard/engineer`, { headers: await authHeaders() });
    return handle<any>(res);
  },
  analytics: async () => {
    const res = await fetch(`${API_URL}/api/dashboard/analytics`, { headers: await authHeaders() });
    return handle<any>(res);
  },
  notifications: async () => {
    const res = await fetch(`${API_URL}/api/dashboard/notifications`, { headers: await authHeaders() });
    return handle<{ notifications: any[] }>(res);
  },
  projectsBoard: async () => {
    const res = await fetch(`${API_URL}/api/dashboard/board`, { headers: await authHeaders() });
    return handle<{ columns: any[]; total_projects: number; total_to_validate: number }>(res);
  },
  veilleDigest: async () => {
    const res = await fetch(`${API_URL}/api/veille/digest`, { headers: await authHeaders() });
    return handle<{ nb_alerts: number; summary_md: string; alerts: any[]; canton: string; period: string }>(res);
  },
  extractEnvelopeFromIfc: async (ifcDocumentId: string) => {
    const res = await fetch(`${API_URL}/api/bim/extract-envelope`, {
      method: 'POST',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ ifc_document_id: ifcDocumentId }),
    });
    return handle<any>(res);
  },
  certificationStatus: async () => {
    const res = await fetch(`${API_URL}/api/certification/status`, { headers: await authHeaders() });
    return handle<any>(res);
  },

  // Onboarding
  onboarding: {
    getState: async () => {
      const res = await fetch(`${API_URL}/api/onboarding/state`, { headers: await authHeaders() });
      return handle<{ completed: boolean; step: number; steps: any[] }>(res);
    },
    stepOrganization: async (body: any) => {
      const res = await fetch(`${API_URL}/api/onboarding/step/organization`, {
        method: 'POST', headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      return handle<any>(res);
    },
    stepBranding: async (body: any) => {
      const res = await fetch(`${API_URL}/api/onboarding/step/branding`, {
        method: 'POST', headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      return handle<any>(res);
    },
    stepFirstProject: async (body: any) => {
      const res = await fetch(`${API_URL}/api/onboarding/step/first-project`, {
        method: 'POST', headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      return handle<{ step: number; completed: boolean; project_id: string }>(res);
    },
    skip: async () => {
      const res = await fetch(`${API_URL}/api/onboarding/skip`, {
        method: 'POST', headers: await authHeaders(),
      });
      return handle<any>(res);
    },
  },

  // Settings — charte client (branding)
  settings: {
    getBranding: async () => {
      const res = await fetch(`${API_URL}/api/settings/branding`, { headers: await authHeaders() });
      return handle<{ organization_name: string; branding_config: any }>(res);
    },
    updateBranding: async (config: any) => {
      const res = await fetch(`${API_URL}/api/settings/branding`, {
        method: 'PUT',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      return handle<any>(res);
    },
  },

  // Billing (V5) — usage + credit packs
  billing: {
    getUsage: async () => {
      const res = await fetch(`${API_URL}/api/billing/usage`, { headers: await authHeaders() });
      return handle<any>(res);
    },
    purchaseCreditPack: async (quantity = 1) => {
      const res = await fetch(`${API_URL}/api/billing/credit-pack/checkout`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity }),
      });
      return handle<{ checkout_url: string; quantity: number }>(res);
    },
  },

  // Billing (legacy V1)
  getBillingStatus: async () => {
    const res = await fetch(`${API_URL}/api/billing/status`, { headers: await authHeaders() });
    return handle<any>(res);
  },
  checkout: async (plan: 'starter' | 'pro' | 'enterprise') => {
    const res = await fetch(`${API_URL}/api/billing/checkout`, {
      method: 'POST',
      headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan }),
    });
    return handle<{ checkout_url: string }>(res);
  },
  billingPortal: async () => {
    const res = await fetch(`${API_URL}/api/billing/portal`, { method: 'POST', headers: await authHeaders() });
    return handle<{ portal_url: string }>(res);
  },

  // Dashboard
  dashboardOverview: async () => {
    const res = await fetch(`${API_URL}/api/dashboard/overview`, { headers: await authHeaders() });
    return handle<any>(res);
  },
  dashboardConsumption: async (days = 30) => {
    const res = await fetch(`${API_URL}/api/dashboard/consumption?days=${days}`, { headers: await authHeaders() });
    return handle<{ daily: any[]; by_model: any[] }>(res);
  },
  dashboardAlerts: async () => {
    const res = await fetch(`${API_URL}/api/dashboard/alerts`, { headers: await authHeaders() });
    return handle<{ alerts: any[] }>(res);
  },

  // Namespace dashboard unifié
  dashboard: {
    overview: async () => {
      const res = await fetch(`${API_URL}/api/dashboard/overview`, { headers: await authHeaders() });
      return handle<any>(res);
    },
    consumption: async (days = 30) => {
      const res = await fetch(`${API_URL}/api/dashboard/consumption?days=${days}`, { headers: await authHeaders() });
      return handle<{ daily: any[]; by_model: any[] }>(res);
    },
    alerts: async () => {
      const res = await fetch(`${API_URL}/api/dashboard/alerts`, { headers: await authHeaders() });
      return handle<{ alerts: any[] }>(res);
    },
    compliance: async () => {
      const res = await fetch(`${API_URL}/api/dashboard/compliance`, { headers: await authHeaders() });
      return handle<{ projects: any[] }>(res);
    },
  },

  // ===================== V2 SWISS-FIRST =====================

  // Thermique SIA 380/1
  thermique: {
    engines: async () => {
      const res = await fetch(`${API_URL}/api/thermique/engines`, { headers: await authHeaders() });
      return handle<{ engines: any[] }>(res);
    },
    listModels: async (projectId?: string) => {
      const q = projectId ? `?project_id=${projectId}` : '';
      const res = await fetch(`${API_URL}/api/thermique/models${q}`, { headers: await authHeaders() });
      return handle<{ models: any[] }>(res);
    },
    getModel: async (id: string) => {
      const res = await fetch(`${API_URL}/api/thermique/models/${id}`, { headers: await authHeaders() });
      return handle<any>(res);
    },
    createModel: async (data: any) => {
      const res = await fetch(`${API_URL}/api/thermique/models`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return handle<any>(res);
    },
    run: async (id: string, body: { engine: 'lesosai_stub' | 'lesosai_file'; author_name?: string; generate_justificatif?: boolean }) => {
      const res = await fetch(`${API_URL}/api/thermique/models/${id}/run`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: id, ...body }),
      });
      return handle<any>(res);
    },
    importResults: async (id: string, pdf: File, authorName?: string) => {
      const form = new FormData();
      form.append('pdf', pdf);
      if (authorName) form.append('author_name', authorName);
      const res = await fetch(`${API_URL}/api/thermique/models/${id}/import-results`, {
        method: 'POST',
        headers: await authHeaders(),
        body: form,
      });
      return handle<any>(res);
    },
  },

  // Structure SIA / SAF
  structure: {
    listModels: async (projectId?: string) => {
      const q = projectId ? `?project_id=${projectId}` : '';
      const res = await fetch(`${API_URL}/api/structure/models${q}`, { headers: await authHeaders() });
      return handle<{ models: any[] }>(res);
    },
    getModel: async (id: string) => {
      const res = await fetch(`${API_URL}/api/structure/models/${id}`, { headers: await authHeaders() });
      return handle<any>(res);
    },
    createModel: async (data: any) => {
      const res = await fetch(`${API_URL}/api/structure/models`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return handle<any>(res);
    },
    generateSaf: async (id: string) => {
      const res = await fetch(`${API_URL}/api/structure/models/${id}/generate-saf`, {
        method: 'POST',
        headers: await authHeaders(),
      });
      return handle<any>(res);
    },
    importResults: async (id: string, safResults: File, engineerValidated: boolean, authorName?: string) => {
      const form = new FormData();
      form.append('saf_results', safResults);
      form.append('engineer_validated', String(engineerValidated));
      if (authorName) form.append('author_name', authorName);
      const res = await fetch(`${API_URL}/api/structure/models/${id}/import-results`, {
        method: 'POST',
        headers: await authHeaders(),
        body: form,
      });
      return handle<any>(res);
    },
  },

  // Pré-BIM
  bim: {
    compositions: async () => {
      const res = await fetch(`${API_URL}/api/bim/compositions`, { headers: await authHeaders() });
      return handle<{ compositions: any[] }>(res);
    },
    premodelFromText: async (data: { program_text: string; project_id?: string; hints?: any }) => {
      const res = await fetch(`${API_URL}/api/bim/premodel/from-text`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return handle<any>(res);
    },
    premodelFromSpec: async (data: { spec: any; project_id?: string }) => {
      const res = await fetch(`${API_URL}/api/bim/premodel/from-spec`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return handle<any>(res);
    },
    listPremodels: async (projectId?: string) => {
      const q = projectId ? `?project_id=${projectId}` : '';
      const res = await fetch(`${API_URL}/api/bim/premodels${q}`, { headers: await authHeaders() });
      return handle<{ premodels: any[] }>(res);
    },
    validate: async (id: string) => {
      const res = await fetch(`${API_URL}/api/bim/premodels/${id}/validate`, {
        method: 'POST',
        headers: await authHeaders(),
      });
      return handle<any>(res);
    },
  },

  // IDC Genève
  idc: {
    listBuildings: async () => {
      const res = await fetch(`${API_URL}/api/idc/buildings`, { headers: await authHeaders() });
      return handle<{ buildings: any[] }>(res);
    },
    getBuilding: async (id: string) => {
      const res = await fetch(`${API_URL}/api/idc/buildings/${id}`, { headers: await authHeaders() });
      return handle<any>(res);
    },
    createBuilding: async (data: any) => {
      const res = await fetch(`${API_URL}/api/idc/buildings`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return handle<any>(res);
    },
    extractInvoice: async (buildingId: string, pdf: File) => {
      const form = new FormData();
      form.append('pdf', pdf);
      const res = await fetch(`${API_URL}/api/idc/buildings/${buildingId}/extract-invoice`, {
        method: 'POST',
        headers: await authHeaders(),
        body: form,
      });
      return handle<any>(res);
    },
    createDeclaration: async (data: any) => {
      const res = await fetch(`${API_URL}/api/idc/declarations`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return handle<any>(res);
    },
    listDeclarations: async (buildingId?: string, year?: number) => {
      const qs = new URLSearchParams();
      if (buildingId) qs.set('building_id', buildingId);
      if (year) qs.set('year', String(year));
      const res = await fetch(`${API_URL}/api/idc/declarations?${qs}`, { headers: await authHeaders() });
      return handle<{ declarations: any[] }>(res);
    },
  },

  // AEAI
  aeai: {
    createChecklist: async (data: any) => {
      const res = await fetch(`${API_URL}/api/aeai/checklists`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return handle<any>(res);
    },
    listChecklists: async (projectId?: string) => {
      const q = projectId ? `?project_id=${projectId}` : '';
      const res = await fetch(`${API_URL}/api/aeai/checklists${q}`, { headers: await authHeaders() });
      return handle<{ checklists: any[] }>(res);
    },
    getChecklist: async (id: string) => {
      const res = await fetch(`${API_URL}/api/aeai/checklists/${id}`, { headers: await authHeaders() });
      return handle<any>(res);
    },
    updateChecklist: async (id: string, data: any) => {
      const res = await fetch(`${API_URL}/api/aeai/checklists/${id}`, {
        method: 'PATCH',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return handle<any>(res);
    },
    exportPdf: async (id: string) => {
      const res = await fetch(`${API_URL}/api/aeai/checklists/${id}/export-pdf`, {
        method: 'POST',
        headers: await authHeaders(),
      });
      return handle<{ pdf_url: string }>(res);
    },
  },

  // Veille réglementaire CH
  veille: {
    listAlerts: async (level?: string, limit = 50) => {
      const qs = new URLSearchParams();
      if (level) qs.set('level', level);
      qs.set('limit', String(limit));
      const res = await fetch(`${API_URL}/api/veille/alerts?${qs}`, { headers: await authHeaders() });
      return handle<{ alerts: any[] }>(res);
    },
    runNow: async () => {
      const res = await fetch(`${API_URL}/api/veille/run-now`, {
        method: 'POST',
        headers: await authHeaders(),
      });
      return handle<any>(res);
    },
  },

  // Normes
  norms: {
    list: async (params?: { domain?: string; jurisdiction?: string; search?: string; quotable_only?: boolean }) => {
      const qs = new URLSearchParams();
      if (params?.domain) qs.set('domain', params.domain);
      if (params?.jurisdiction) qs.set('jurisdiction', params.jurisdiction);
      if (params?.search) qs.set('search', params.search);
      if (params?.quotable_only) qs.set('quotable_only', 'true');
      const res = await fetch(`${API_URL}/api/norms?${qs}`, { headers: await authHeaders() });
      return handle<{ norms: any[]; count: number }>(res);
    },
    get: async (id: string) => {
      const res = await fetch(`${API_URL}/api/norms/${id}`, { headers: await authHeaders() });
      return handle<any>(res);
    },
  },

  // V3 — Connecteurs directs (pas de DB, réponse immédiate)
  v3: {
    // Thermique
    simulate: async (formData: FormData) => {
      const res = await fetch(`${API_URL}/api/thermique/v3/simulate`, {
        method: 'POST',
        headers: await authHeadersNoContent(),
        body: formData,
      });
      return handle<any>(res);
    },
    gbxml: async (formData: FormData): Promise<Blob> => {
      const res = await fetch(`${API_URL}/api/thermique/v3/gbxml`, {
        method: 'POST',
        headers: await authHeadersNoContent(),
        body: formData,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.blob();
    },

    // IDC
    extractFacture: async (formData: FormData) => {
      const res = await fetch(`${API_URL}/api/idc/v3/extract-facture`, {
        method: 'POST',
        headers: await authHeadersNoContent(),
        body: formData,
      });
      return handle<{
        value: number | null;
        unit: string | null;
        period_start: string | null;
        period_end: string | null;
        confidence: number;
        extraction_method: string;
        warnings: string[];
      }>(res);
    },
    computeIDC: async (body: {
      sre_m2: number;
      vector: string;
      affectation?: string;
      year?: number;
      dju_year?: number;
      consumptions: Array<{ value: number; unit: string; period_start?: string; period_end?: string }>;
    }) => {
      const res = await fetch(`${API_URL}/api/idc/v3/compute`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      return handle<any>(res);
    },
    ocenForm: async (body: { calculation: any; building: any }): Promise<Blob> => {
      const res = await fetch(`${API_URL}/api/idc/v3/ocen-form`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.blob();
    },

    // Structure
    generateSAF: async (body: { nodes: any[]; members: any[]; supports?: any[]; loads?: any[]; project_info?: any }): Promise<Blob> => {
      const res = await fetch(`${API_URL}/api/structure/v3/saf`, {
        method: 'POST',
        headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.blob();
    },
    doubleCheck: async (formData: FormData) => {
      const res = await fetch(`${API_URL}/api/structure/v3/double-check`, {
        method: 'POST',
        headers: await authHeadersNoContent(),
        body: formData,
      });
      return handle<any>(res);
    },
  },

  // =======================
  // V4 — Agents haute valeur ajoutée
  // =======================
  v4: {
    dossierEnquete: {
      create: async (body: any) => {
        const res = await fetch(`${API_URL}/api/v4/dossier-enquete`, {
          method: 'POST',
          headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        return handle<any>(res);
      },
      list: async (project_id?: string) => {
        const url = new URL(`${API_URL}/api/v4/dossier-enquete`);
        if (project_id) url.searchParams.set('project_id', project_id);
        const res = await fetch(url, { headers: await authHeaders() });
        return handle<{ dossiers: any[] }>(res);
      },
      get: async (id: string) => {
        const res = await fetch(`${API_URL}/api/v4/dossier-enquete/${id}`, {
          headers: await authHeaders(),
        });
        return handle<any>(res);
      },
    },
    observations: {
      create: async (body: any) => {
        const res = await fetch(`${API_URL}/api/v4/observations`, {
          method: 'POST',
          headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        return handle<any>(res);
      },
      upload: async (formData: FormData) => {
        const res = await fetch(`${API_URL}/api/v4/observations/upload`, {
          method: 'POST',
          headers: await authHeadersNoContent(),
          body: formData,
        });
        return handle<any>(res);
      },
      list: async (project_id?: string) => {
        const url = new URL(`${API_URL}/api/v4/observations`);
        if (project_id) url.searchParams.set('project_id', project_id);
        const res = await fetch(url, { headers: await authHeaders() });
        return handle<{ observations: any[] }>(res);
      },
    },
    simulationRapide: {
      create: async (body: any) => {
        const res = await fetch(`${API_URL}/api/v4/simulation-rapide`, {
          method: 'POST',
          headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        return handle<any>(res);
      },
      list: async (project_id?: string) => {
        const url = new URL(`${API_URL}/api/v4/simulation-rapide`);
        if (project_id) url.searchParams.set('project_id', project_id);
        const res = await fetch(url, { headers: await authHeaders() });
        return handle<{ simulations: any[] }>(res);
      },
    },
    metres: {
      extract: async (formData: FormData) => {
        const res = await fetch(`${API_URL}/api/v4/metres/extract`, {
          method: 'POST',
          headers: await authHeadersNoContent(),
          body: formData,
        });
        return handle<any>(res);
      },
      list: async (project_id?: string) => {
        const url = new URL(`${API_URL}/api/v4/metres`);
        if (project_id) url.searchParams.set('project_id', project_id);
        const res = await fetch(url, { headers: await authHeaders() });
        return handle<{ metres: any[] }>(res);
      },
    },
    dashboard: async () => {
      const res = await fetch(`${API_URL}/api/v4/compliance-dashboard`, {
        headers: await authHeaders(),
      });
      return handle<{ projects: any[] }>(res);
    },
  },
};
