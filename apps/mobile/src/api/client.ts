/**
 * Janvaani Mobile API Client
 * Centralized, typed HTTP client for interacting with the Janvaani NLP FastAPI backend.
 * 
 * Supports:
 * - Dynamic configurable base URL for Android emulator (10.0.2.2), physical Android phone (10.216.94.61), iOS/web (localhost), or AWS.
 * - Bearer authentication header with dev token or Firebase token.
 * - Request timeouts, typed ApiError, and safe retry for idempotent read calls only.
 * - Strict type-safety matching backend Pydantic schemas.
 * - Speech-to-Text (ASR) and Text-to-Speech (TTS) integration.
 */

// Safe detection of Android platform without crashing in test runners
let isAndroid = false;
try {
  const rn = require('react-native');
  if (rn && rn.Platform && rn.Platform.OS === 'android') {
    isAndroid = true;
  }
} catch {
  // Non-React-Native test environment
}

// Auto-detect development machine IP from Expo/Metro connection
let detectedHost = '10.142.122.61';
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const Constants = require('expo-constants').default;
  const hostUri =
    Constants?.expoConfig?.hostUri ||
    Constants?.manifest2?.extra?.expoClient?.hostUri ||
    Constants?.manifest?.debuggerHost;
  if (hostUri) {
    const ip = hostUri.split(':')[0];
    if (ip && ip !== 'localhost' && ip !== '127.0.0.1') {
      detectedHost = ip;
    }
  }
} catch {
  // Non-Expo or test environment
}

const DEFAULT_HOST = 'https://janvaani-backend-5u0z.onrender.com';

export const API_BASE_URL =
  (typeof process !== 'undefined' && process.env?.EXPO_PUBLIC_API_URL) || DEFAULT_HOST;

const CANDIDATE_BASE_URLS = [
  'https://janvaani-backend-5u0z.onrender.com',
  API_BASE_URL,
].filter((u, idx, self) => u && self.indexOf(u) === idx);

let dynamicBaseUrl: string | null = null;

export const setApiBaseUrl = (url: string | null) => {
  dynamicBaseUrl = url;
};

export const getApiBaseUrl = (): string => {
  return dynamicBaseUrl || API_BASE_URL;
};

const DEFAULT_TIMEOUT_MS = 25000;
const OCR_TIMEOUT_MS = 45000;

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// --- Data Types Matching Backend Schemas ---

export interface UserProfile {
  preferred_language: string;
  state: string | null;
  district: string | null;
  attributes: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface UserProfileUpdate {
  preferred_language?: string;
  state?: string | null;
  district?: string | null;
  attributes?: Record<string, any>;
}

export interface SchemeVersionSummary {
  version_number: number;
  language: string;
  description: string;
}

export interface SchemeSummary {
  slug: string;
  title: string;
  administering_authority: string;
  government_level: 'central' | 'state' | 'local' | 'other';
  versions: SchemeVersionSummary[];
}

export interface SchemeVersionDetail extends SchemeVersionSummary {
  benefits: string;
  eligibility_criteria: Record<string, any>;
  required_documents: string[];
  application_process: string;
  valid_from?: string | null;
  valid_until?: string | null;
}

export interface SchemeDetail {
  slug: string;
  title: string;
  administering_authority: string;
  government_level: 'central' | 'state' | 'local' | 'other';
  versions: SchemeVersionDetail[];
}

export interface RuleEvaluationCondition {
  rule_id: string;
  field: string;
  operator: string;
  expected: any;
  actual: any;
  satisfied: boolean | null;
  explanation: string;
  supported: boolean;
  required: boolean;
}

export type EligibilityStatus = 'ELIGIBLE' | 'NOT_ELIGIBLE' | 'INSUFFICIENT_INFORMATION';

export interface EligibilityResult {
  status: EligibilityStatus;
  conditions: RuleEvaluationCondition[];
  missing_fields: string[];
  summary: string;
  explanation?: string;
  reason_code?: string;
  review_status?: string;
}

export interface ChatSourceCitation {
  scheme_id?: string;
  scheme_title?: string;
  section?: string;
  snippet?: string;
  source_url?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSourceCitation[];
  created_at?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  language: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail {
  id: string;
  title: string;
  language: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface DocumentValidationIssue {
  field: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
}

export interface DocumentExtractResult {
  document_id: string;
  document_type: string;
  raw_text: string;
  fields: Record<string, any>;
  validation: {
    is_valid: boolean;
    issues: DocumentValidationIssue[];
    confidence: number;
  };
  profile_conflicts: DocumentValidationIssue[];
  provider: string;
  review_required: boolean;
  authenticity_verified: boolean;
}

export interface ApplicationReadinessChecklist {
  document_type: string;
  status: 'submitted' | 'missing' | 'unverified';
  note?: string;
}

export interface ApplicationReadinessResult {
  scheme_id: string;
  scheme_title: string;
  scheme_version: number;
  review_status: string;
  overall_ready: boolean;
  checklist: ApplicationReadinessChecklist[];
  missing_documents: string[];
  unverified_documents: string[];
}

// --- In-Memory Auth & Token State ---
let authToken: string | null = 'local-dev-token'; // Defaults to dev token for seamless local integration
let onUnauthorizedCallback: (() => void) | null = null;

export const setAuthToken = (token: string | null) => {
  authToken = token;
};

export const getAuthToken = (): string | null => {
  return authToken;
};

export const setOnUnauthorized = (callback: (() => void) | null) => {
  onUnauthorizedCallback = callback;
};

// --- HTTP Fetch Helper with Timeout & Safe Retries ---
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
  retries = 1,
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint}`;
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Bypass-Tunnel-Reminder': 'true',
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData) && !(options.body instanceof Uint8Array) && typeof options.body === 'string') {
    if (!headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }
  }

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (response.status === 401) {
      if (onUnauthorizedCallback) {
        onUnauthorizedCallback();
      }
      let errDetail = 'Unauthorized session';
      try {
        const errJson = await response.json();
        errDetail = errJson.detail || errDetail;
      } catch {
        // ignore json parse error
      }
      throw new ApiError(errDetail, 401);
    }

    if (!response.ok) {
      let errDetail = `HTTP ${response.status} Error`;
      let errData = null;
      try {
        errData = await response.json();
        if (errData && errData.detail) {
          errDetail = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
        }
      } catch {
        // Non-JSON response
      }
      throw new ApiError(errDetail, response.status, errData);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  } catch (error: any) {
    clearTimeout(timeoutId);

    // Auto-failover to next candidate if network error or timeout
    const currentBase = baseUrl;
    const isNetworkOrTimeout =
      error?.name === 'AbortError' ||
      !(error instanceof ApiError) ||
      error.status === 0 ||
      error.status === 502 ||
      error.status === 503 ||
      error.status === 504;
    if (isNetworkOrTimeout && (!dynamicBaseUrl || retries > 0)) {
      const nextCandidates = CANDIDATE_BASE_URLS.filter((c) => c !== currentBase);
      for (const candidate of nextCandidates) {
        try {
          const testCtrl = new AbortController();
          const tId = setTimeout(() => testCtrl.abort(), 2500);
          const testRes = await fetch(`${candidate}/health`, {
            headers: { 'Bypass-Tunnel-Reminder': 'true' },
            signal: testCtrl.signal,
          });
          clearTimeout(tId);
          if (testRes.ok) {
            console.log(`[JanvaaniApi] Auto-switched API endpoint from ${currentBase} to ${candidate}`);
            dynamicBaseUrl = candidate;
            return apiRequest<T>(endpoint, options, 0, timeoutMs);
          }
        } catch {
          // Continue to next candidate
        }
      }
    }

    if (error?.name === 'AbortError') {
      throw new ApiError(`Request timeout after ${timeoutMs}ms (${url})`, 408);
    }

    // Safe retry for GET calls if network error and retries remaining
    const isGet = !options.method || options.method.toUpperCase() === 'GET';
    if (isGet && retries > 0 && !(error instanceof ApiError && error.status < 500)) {
      return apiRequest<T>(endpoint, options, retries - 1, timeoutMs);
    }

    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(error?.message || `Network request failed to ${url}`, 0);
  }
}

// --- Centralized API Services ---

export const JanvaaniApi = {
  // System Health
  checkHealth: async (): Promise<{ status: string }> => {
    return apiRequest<{ status: string }>('/health', {}, 1, 5000);
  },

  // Citizen Profile
  getProfile: async (): Promise<UserProfile> => {
    return apiRequest<UserProfile>('/profiles/me');
  },

  updateProfile: async (updates: UserProfileUpdate): Promise<UserProfile> => {
    return apiRequest<UserProfile>(
      '/profiles/me',
      {
        method: 'PATCH',
        body: JSON.stringify(updates),
      },
      0 // No retries on non-idempotent mutations
    );
  },

  // Scheme Discovery
  listSchemes: async (params?: { government_level?: string; limit?: number; offset?: number; language?: string }): Promise<SchemeSummary[]> => {
    const query = new URLSearchParams();
    if (params?.government_level) query.append('government_level', params.government_level);
    if (params?.limit) query.append('limit', String(params.limit));
    if (params?.offset) query.append('offset', String(params.offset));
    if (params?.language) query.append('language', params.language);
    const qs = query.toString();
    return apiRequest<SchemeSummary[]>(`/schemes${qs ? `?${qs}` : ''}`);
  },

  getScheme: async (slug: string, language = 'en'): Promise<SchemeDetail> => {
    const langParam = language && language !== 'en' ? `?language=${encodeURIComponent(language)}` : '';
    return apiRequest<SchemeDetail>(`/schemes/${encodeURIComponent(slug)}${langParam}`);
  },

  // Eligibility Evaluation
  evaluateEligibility: async (payload: {
    scheme_id: string;
    scheme_name: string;
    rule_version: string;
    rules: Array<{
      rule_id: string;
      field: string;
      operator: string;
      expected: any;
      explanation?: string;
      supported?: boolean;
      required?: boolean;
    }>;
    profile: Record<string, any>;
    language?: string;
  }): Promise<EligibilityResult> => {
    const langParam = payload.language && payload.language !== 'en' ? `?language=${encodeURIComponent(payload.language)}` : '';
    return apiRequest<EligibilityResult>(
      `/api/eligibility/evaluate${langParam}`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      0
    );
  },

  evaluateReviewedScheme: async (payload: {
    scheme_id: string;
    profile: Record<string, any>;
    language?: string;
  }): Promise<EligibilityResult> => {
    const langParam = payload.language && payload.language !== 'en' ? `?language=${encodeURIComponent(payload.language)}` : '';
    return apiRequest<EligibilityResult>(
      `/api/eligibility/evaluate-reviewed${langParam}`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      0
    );
  },

  // Persistent Chat & RAG
  listConversations: async (): Promise<ConversationSummary[]> => {
    return apiRequest<ConversationSummary[]>('/api/chat/conversations');
  },

  createConversation: async (title?: string, initialMessage?: string, language = 'en'): Promise<ConversationSummary> => {
    return apiRequest<ConversationSummary>(
      '/api/chat/conversations',
      {
        method: 'POST',
        body: JSON.stringify({
          title: title || undefined,
          language: language || 'en',
          initial_message: initialMessage || undefined,
        }),
      },
      0
    );
  },

  getConversation: async (conversationId: string): Promise<ConversationDetail> => {
    return apiRequest<ConversationDetail>(`/api/chat/conversations/${encodeURIComponent(conversationId)}`);
  },

  sendMessage: async (
    conversationId: string,
    content: string,
    language = 'en'
  ): Promise<{ user_message: ChatMessage; assistant_message: ChatMessage }> => {
    const rawResult = await apiRequest<any>(
      `/api/chat/conversations/${encodeURIComponent(conversationId)}/messages`,
      {
        method: 'POST',
        body: JSON.stringify({
          message: content,
          content: content,
          language: language || 'en',
        }),
      },
      0 // No retries on message submission
    );

    const assistantMsg: ChatMessage = {
      id: rawResult.id || rawResult.assistant_message?.id || `msg-${Date.now()}`,
      role: 'assistant',
      content: rawResult.content || rawResult.assistant_message?.content || '',
      sources: rawResult.sources || rawResult.assistant_message?.sources || [],
      created_at: rawResult.created_at || rawResult.assistant_message?.created_at || new Date().toISOString(),
    };

    const userMsg: ChatMessage = rawResult.user_message || {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    return { user_message: userMsg, assistant_message: assistantMsg };
  },

  sendStatelessMessage: async (
    message: string,
    history: Array<{ role: string; content: string }> = [],
    language = 'en'
  ): Promise<{ response: string; sources: ChatSourceCitation[]; language: string }> => {
    const res = await apiRequest<{ question?: string; answer?: string; response?: string; sources: ChatSourceCitation[]; language?: string }>(
      '/api/chat',
      {
        method: 'POST',
        body: JSON.stringify({ message, history, language: language || 'en' }),
      },
      0
    );
    return {
      response: res.answer || res.response || '',
      sources: res.sources || [],
      language: res.language || language || 'en',
    };
  },

  deleteConversation: async (conversationId: string): Promise<void> => {
    return apiRequest<void>(
      `/api/chat/conversations/${encodeURIComponent(conversationId)}`,
      {
        method: 'DELETE',
      },
      0
    );
  },

  // Document Vault & OCR
  extractDocument: async (payload: {
    file_base64: string;
    mime_type?: string;
    document_type?: string;
    language?: string;
    preferred_provider?: string;
  }): Promise<DocumentExtractResult> => {
    const docType = payload.document_type || 'income_certificate';
    const lang = payload.language || 'en';
    const providerParam = payload.preferred_provider ? `&preferred_provider=${encodeURIComponent(payload.preferred_provider)}` : '';

    return apiRequest<DocumentExtractResult>(
      `/api/documents/extract?document_type=${encodeURIComponent(docType)}&language=${encodeURIComponent(lang)}${providerParam}`,
      {
        method: 'POST',
        body: JSON.stringify({
          file_base64: payload.file_base64,
          mime_type: payload.mime_type || 'image/jpeg',
          document_type: docType,
          language: lang,
          preferred_provider: payload.preferred_provider || null,
        }),
      },
      0, // No retry on OCR upload
      OCR_TIMEOUT_MS
    );
  },

  checkApplicationReadiness: async (
    schemeId: string,
    submittedDocumentTypes: string[],
    language = 'en'
  ): Promise<ApplicationReadinessResult> => {
    return apiRequest<ApplicationReadinessResult>(
      '/api/applications/readiness',
      {
        method: 'POST',
        body: JSON.stringify({
          scheme_id: schemeId,
          submitted_document_types: submittedDocumentTypes,
          language,
        }),
      },
      0
    );
  },

  // Speech Services (ASR & TTS)
  transcribeAudioBase64: async (
    audioBase64: string,
    language = 'en'
  ): Promise<{ text: string; language: string }> => {
    return apiRequest<{ text: string; language: string }>(
      `/speech/asr?language=${encodeURIComponent(language)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio_base64: audioBase64 }),
      },
      0,
      25000
    );
  },

  transcribeAudio: async (
    audioWavBytes: any,
    language = 'en',
    mimeType = 'audio/wav'
  ): Promise<{ text: string; language: string }> => {
    return apiRequest<{ text: string; language: string }>(
      `/speech/asr?language=${encodeURIComponent(language)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': mimeType },
        body: audioWavBytes,
      },
      0,
      20000
    );
  },

  synthesizeSpeech: async (
    text: string,
    language = 'hi',
    gender: 'male' | 'female' = 'male'
  ): Promise<Blob> => {
    const url = `${getApiBaseUrl()}/speech/tts`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'audio/wav',
    };
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({ text, language, gender }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        throw new ApiError(`TTS service failed with status ${res.status}`, res.status);
      }
      return await res.blob();
    } catch (err: any) {
      clearTimeout(timeoutId);
      if (err instanceof ApiError) throw err;
      throw new ApiError(err?.message || 'Speech synthesis network request failed', 0);
    }
  },
};
