/**
 * Types mirroring the API contract in docs/api-spec.md.
 *
 * Every endpoint returns the same envelope, including on failure - which is
 * what lets the Emergency tab fall back to bundled content instead of
 * rendering a blank screen.
 */

export interface Meta {
  source: string;
  cached: boolean;
  took_ms: number;
  index?: string;
  agent?: string | null;
}

export interface ApiError {
  code:
    | 'BAD_REQUEST'
    | 'FORBIDDEN'
    | 'NOT_FOUND'
    | 'RATE_LIMITED'
    | 'UPSTREAM_ERROR'
    | 'INTERNAL_ERROR'
    | 'NOT_IMPLEMENTED';
  message: string;
  retryable?: boolean;
  cedar?: { decision: string; reasons: string[] };
  [key: string]: unknown;
}

export type Envelope<T> =
  | { ok: true; data: T; error: null; meta: Meta }
  | { ok: false; data: null; error: ApiError; meta: Meta };

export interface ListOf<T> {
  items: T[];
  count: number;
  total?: number;
}

// --- Emergency --------------------------------------------------------------

export type Severity = 'critical' | 'high' | 'moderate';

export interface Protocol {
  scenario_id: string;
  title: string;
  severity: Severity;
  subtitle?: string;
  steps: string[];
  do_not: string[];
  tags?: string[];
}

export interface EmergencyNumbers {
  state: string | null;
  matched: boolean;
  ambulance: string;
  police: string;
  fire: string;
  unified: string;
  note: string;
}

export interface GoodSamaritan {
  title: string;
  points: string[];
  source: string;
  disclaimer: string;
}

/** Answer to "Is the person breathing?" -> the protocol to show. */
export type TriageAnswer = 'yes' | 'no' | 'unsure';

// --- Aftermath --------------------------------------------------------------

export type StageId = 'hospital' | 'police' | 'insurance' | 'legal';

export interface Stage {
  stage_id: StageId;
  order: number;
  title: string;
  subtitle?: string;
  checklist: string[];
  details: string[];
  tags?: string[];
}

export type Topic =
  | 'good_samaritan'
  | 'hospital'
  | 'fir'
  | 'insurance'
  | 'legal_aid'
  | 'compensation';

export interface Faq {
  faq_id: string;
  question: string;
  answer: string;
  topic: Topic;
  tags?: string[];
  score?: number;
}

export interface FaqResults extends ListOf<Faq> {
  topic: Topic | null;
  query: string | null;
}

// --- Resources --------------------------------------------------------------

export type ResourceType = 'hospital' | 'legal_aid' | 'ngo' | 'scheme';

export interface Resource {
  resource_id: string;
  name: string;
  type: ResourceType;
  state: string;
  city: string;
  address: string;
  description: string;
  hours?: string;
  contact: { phone?: string; alt_phone?: string; website?: string };
  geo?: { lat: number; lon: number };
  /** Present only when lat/lon were supplied. null = this record has no coordinates. */
  distance_km?: number | null;
  tags?: string[];
}

// --- AI ---------------------------------------------------------------------

export interface AiAction {
  type: 'call' | 'open_protocol' | 'open_stage' | 'open_resources';
  label: string;
  value: string;
}

export interface EmergencyAiReply {
  session_id: string;
  reply: string;
  steps: string[];
  protocol_id: string | null;
  severity: Severity | null;
  actions: AiAction[];
  disclaimer: string;
}

export interface AftermathAiReply {
  session_id: string;
  reply: string;
  citations: Array<{ faq_id?: string; question?: string; stage_id?: string; title?: string }>;
  suggested_next: AiAction[];
  disclaimer: string;
}
