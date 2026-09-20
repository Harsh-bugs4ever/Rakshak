/**
 * Typed API client.
 *
 * Two rules drive the design:
 *
 * 1. Emergency reads must never leave the user staring at a spinner. Every
 *    emergency call has a short timeout and a bundled fallback, because a slow
 *    network at a crash scene should cost milliseconds, not the whole screen.
 * 2. Errors are values, not exceptions. The envelope is returned as-is so the
 *    caller decides what to render - the UI always has something to show.
 */

import type {
  AftermathAiReply,
  EmergencyAiReply,
  EmergencyNumbers,
  Envelope,
  Faq,
  FaqResults,
  GoodSamaritan,
  ListOf,
  Protocol,
  Resource,
  ResourceType,
  Stage,
  StageId,
  Topic,
} from './types';

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:3000';

/** Emergency reads bail out fast; the bundled protocols are already on device. */
const EMERGENCY_TIMEOUT_MS = 2500;
const DEFAULT_TIMEOUT_MS = 8000;

function offlineEnvelope<T>(message: string): Envelope<T> {
  return {
    ok: false,
    data: null,
    error: { code: 'UPSTREAM_ERROR', message, retryable: true },
    meta: { source: 'offline', cached: false, took_ms: 0 },
  };
}

async function request<T>(
  path: string,
  params: Record<string, string | number | undefined> = {},
  init: RequestInit & { timeoutMs?: number } = {},
): Promise<Envelope<T>> {
  const url = new URL(BASE.replace(/\/$/, '') + path);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') url.searchParams.set(key, String(value));
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), init.timeoutMs ?? DEFAULT_TIMEOUT_MS);

  try {
    const response = await fetch(url.toString(), {
      ...init,
      signal: controller.signal,
      headers: { Accept: 'application/json', ...(init.headers ?? {}) },
    });
    // 4xx and 5xx still carry a valid envelope, so parse rather than throw.
    return (await response.json()) as Envelope<T>;
  } catch {
    return offlineEnvelope<T>('Could not reach the server.');
  } finally {
    clearTimeout(timeout);
  }
}

// --- Emergency --------------------------------------------------------------

export const getProtocol = (scenario: string) =>
  request<Protocol>('/emergency/protocols', { scenario }, { timeoutMs: EMERGENCY_TIMEOUT_MS });

export const listProtocols = () =>
  request<ListOf<Protocol>>('/emergency/protocols', {}, { timeoutMs: EMERGENCY_TIMEOUT_MS });

export const getNumbers = (state?: string) =>
  request<EmergencyNumbers>('/emergency/numbers', { state }, { timeoutMs: EMERGENCY_TIMEOUT_MS });

export const getGoodSamaritan = () =>
  request<GoodSamaritan>('/emergency/good-samaritan', {}, { timeoutMs: EMERGENCY_TIMEOUT_MS });

// --- Aftermath --------------------------------------------------------------

export const getStage = (stage: StageId) => request<Stage>('/aftermath/steps', { stage });

export const listStages = () => request<ListOf<Stage>>('/aftermath/steps');

export const searchFaqs = (opts: { q?: string; topic?: Topic; limit?: number } = {}) =>
  request<FaqResults>('/aftermath/faqs', opts);

export const listFaqsByTopic = (topic: Topic) => request<ListOf<Faq>>('/aftermath/faqs', { topic });

// --- Resources --------------------------------------------------------------

export interface ResourceQuery {
  type?: ResourceType;
  state?: string;
  city?: string;
  q?: string;
  lat?: number;
  lon?: number;
  limit?: number;
}

/** Sending only one of lat/lon is a 400 by design, so drop a lone coordinate. */
export const searchResources = ({ lat, lon, ...rest }: ResourceQuery = {}) =>
  request<ListOf<Resource>>('/resources', {
    ...rest,
    ...(lat !== undefined && lon !== undefined ? { lat, lon } : {}),
  });

// --- AI ---------------------------------------------------------------------
// Grounded reference guidance, with optional local Strands FAQ matching.

async function postAi<T>(path: string, body: unknown): Promise<Envelope<T>> {
  return request<T>(path, {}, {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
    timeoutMs: 15000,
  });
}

export const askEmergency = (message: string, context?: Record<string, unknown>, sessionId?: string) =>
  postAi<EmergencyAiReply>('/ai/emergency', { message, context, session_id: sessionId });

export const askAftermath = (message: string, context?: Record<string, unknown>, sessionId?: string) =>
  postAi<AftermathAiReply>('/ai/aftermath', { message, context, session_id: sessionId });

// --- Health -----------------------------------------------------------------

export const getHealth = () =>
  request<{ healthy: boolean; tables: Record<string, unknown> }>('/health');
