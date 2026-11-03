/**
 * Automated API Contract & Integration Tests for Janvaani Mobile
 * Validates mobile client behavior, payload compatibility, and error handling
 * against backend FastAPI schemas using node:test.
 */

const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');

describe('Janvaani Mobile API Client Contract Tests', () => {
  let originalFetch;
  let mockFetchCalls = [];

  beforeEach(() => {
    originalFetch = global.fetch;
    mockFetchCalls = [];
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  test('Client attaches Bearer token to authenticated requests', async () => {
    global.fetch = async (url, options) => {
      mockFetchCalls.push({ url, options });
      return {
        ok: true,
        status: 200,
        json: async () => ({
          preferred_language: 'hi',
          state: 'Madhya Pradesh',
          district: 'Sehore',
          attributes: { farmer_category: 'small_farmer' },
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        }),
      };
    };

    const { JanvaaniApi, setAuthToken } = await import('../src/api/client.ts');

    setAuthToken('test-dev-token');
    const profile = await JanvaaniApi.getProfile();

    assert.strictEqual(mockFetchCalls.length, 1);
    const headers = mockFetchCalls[0].options.headers;
    assert.strictEqual(headers['Authorization'], 'Bearer test-dev-token');
    assert.strictEqual(profile.preferred_language, 'hi');
    assert.strictEqual(profile.state, 'Madhya Pradesh');
  });

  test('Client triggers onUnauthorized callback and throws ApiError on 401', async () => {
    let unauthorizedTriggered = false;

    global.fetch = async () => ({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid or expired authentication token' }),
    });

    const { JanvaaniApi, setOnUnauthorized, ApiError } = await import('../src/api/client.ts');

    setOnUnauthorized(() => {
      unauthorizedTriggered = true;
    });

    await assert.rejects(
      async () => {
        await JanvaaniApi.getProfile();
      },
      (err) => {
        assert(err instanceof ApiError);
        assert.strictEqual(err.status, 401);
        assert.strictEqual(err.message, 'Invalid or expired authentication token');
        return true;
      }
    );

    assert.strictEqual(unauthorizedTriggered, true);
  });

  test('Eligibility evaluation preserves distinct statuses without false conversions', async () => {
    const statuses = ['ELIGIBLE', 'NOT_ELIGIBLE', 'INSUFFICIENT_INFORMATION'];
    const { JanvaaniApi } = await import('../src/api/client.ts');

    for (const expectedStatus of statuses) {
      global.fetch = async (url, options) => ({
        ok: true,
        status: 200,
        json: async () => ({
          status: expectedStatus,
          conditions: [
            {
              rule_id: 'land_rule',
              field: 'land_hectares',
              operator: '<=',
              expected: 2.0,
              actual: 1.5,
              satisfied: expectedStatus === 'ELIGIBLE',
              explanation: 'Land limit check',
              supported: true,
              required: true,
            },
          ],
          missing_fields: expectedStatus === 'INSUFFICIENT_INFORMATION' ? ['land_hectares'] : [],
          summary: `Evaluated as ${expectedStatus}`,
        }),
      });

      const result = await JanvaaniApi.evaluateEligibility({
        scheme_id: 'pm-kisan',
        scheme_name: 'PM-KISAN',
        rule_version: 'v1',
        rules: [],
        profile: {},
      });

      assert.strictEqual(result.status, expectedStatus);
      if (expectedStatus === 'INSUFFICIENT_INFORMATION') {
        assert(result.missing_fields.includes('land_hectares'));
      }
    }
  });

  test('Document extraction preserves authenticity_verified: false invariant', async () => {
    global.fetch = async (url, options) => ({
      ok: true,
      status: 200,
      json: async () => ({
        document_id: 'doc-123',
        document_type: 'income_certificate',
        raw_text: 'वार्षिक आय: ₹60,000',
        fields: { annual_income: 60000 },
        validation: {
          is_valid: true,
          issues: [],
          confidence: 0.95,
        },
        profile_conflicts: [],
        provider: 'gemini_vision',
        review_required: true,
        authenticity_verified: false,
      }),
    });

    const { JanvaaniApi } = await import('../src/api/client.ts');

    const result = await JanvaaniApi.extractDocument({
      file_base64: 'mock-base64',
      document_type: 'income_certificate',
    });

    assert.strictEqual(result.authenticity_verified, false, 'OCR documents must never be marked authentic');
    assert.strictEqual(result.review_required, true, 'Citizen review must always be required');
    assert.strictEqual(result.provider, 'gemini_vision');
    assert.strictEqual(result.fields.annual_income, 60000);
  });

  test('Persistent chat turn maps user and assistant messages with citations', async () => {
    global.fetch = async (url, options) => ({
      ok: true,
      status: 200,
      json: async () => ({
        user_message: {
          id: 'msg-u1',
          role: 'user',
          content: 'पीएम-किसान की पात्रता क्या है?',
          created_at: '2026-01-01T00:00:00Z',
        },
        assistant_message: {
          id: 'msg-a1',
          role: 'assistant',
          content: 'पीएम-किसान के तहत पात्र किसान परिवारों को ₹6,000 वार्षिक सहायता दी जाती है।',
          sources: [
            {
              scheme_id: '62a70e86f038bd8499a6aa53',
              scheme_title: 'PM-KISAN',
              section: 'eligibility',
              snippet: '2 हेक्टेयर तक की कृषि भूमि...',
              source_url: 'https://pmkisan.gov.in',
            },
          ],
          created_at: '2026-01-01T00:00:01Z',
        },
      }),
    });

    const { JanvaaniApi } = await import('../src/api/client.ts');

    const turn = await JanvaaniApi.sendMessage('conv-1', 'पीएम-किसान की पात्रता क्या है?', 'hi');

    assert.strictEqual(turn.user_message.role, 'user');
    assert.strictEqual(turn.assistant_message.role, 'assistant');
    assert.strictEqual(turn.assistant_message.sources.length, 1);
    assert.strictEqual(turn.assistant_message.sources[0].scheme_title, 'PM-KISAN');
  });

  test('Dynamic Base URL configuration updates the target host for API requests', async () => {
    const { JanvaaniApi, setApiBaseUrl, getApiBaseUrl } = await import('../src/api/client.ts');
    
    setApiBaseUrl('http://10.142.122.61:8000');
    assert.strictEqual(getApiBaseUrl(), 'http://10.142.122.61:8000');

    global.fetch = async (url, options) => {
      mockFetchCalls.push({ url, options });
      return {
        ok: true,
        status: 200,
        json: async () => [],
      };
    };

    await JanvaaniApi.listSchemes();
    assert.strictEqual(mockFetchCalls.length, 1);
    assert(mockFetchCalls[0].url.startsWith('http://10.142.122.61:8000/schemes'));
  });

  test('Speech ASR and TTS endpoints send correct payload and language mappings', async () => {
    const { JanvaaniApi } = await import('../src/api/client.ts');

    global.fetch = async (url, options) => {
      mockFetchCalls.push({ url, options });
      if (url.includes('/speech/asr')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ text: 'मेरी पात्रता क्या है?', language: 'hi' }),
        };
      }
      if (url.includes('/speech/tts')) {
        return {
          ok: true,
          status: 200,
          blob: async () => ({ size: 1024, type: 'audio/wav' }),
        };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    };

    // ASR call
    const asrResult = await JanvaaniApi.transcribeAudio('dummy-audio-bytes', 'hi');
    assert.strictEqual(asrResult.text, 'मेरी पात्रता क्या है?');
    assert.strictEqual(mockFetchCalls[0].options.method, 'POST');
    assert(mockFetchCalls[0].url.includes('/speech/asr?language=hi'));

    // TTS call
    const ttsResult = await JanvaaniApi.synthesizeSpeech('नमस्ते किसान भाई', 'hi');
    assert(ttsResult);
    assert.strictEqual(mockFetchCalls[1].options.method, 'POST');
    const ttsPayload = JSON.parse(mockFetchCalls[1].options.body);
    assert.strictEqual(ttsPayload.text, 'नमस्ते किसान भाई');
    assert.strictEqual(ttsPayload.language, 'hi');
  });

  test('Localization engine returns correct strings for English, Hindi, and regional fallback', async () => {
    const { getTranslation } = await import('../src/i18n/translations.ts');

    // English
    assert.strictEqual(getTranslation('brandTitle', 'en'), 'Janvaani');
    assert.strictEqual(getTranslation('tabHome', 'en'), 'Home');
    assert.strictEqual(getTranslation('eligibleTitle', 'en'), 'ELIGIBLE');

    // Hindi
    assert.strictEqual(getTranslation('brandTitle', 'hi'), 'जनवाणी');
    assert.strictEqual(getTranslation('tabHome', 'hi'), 'होम');
    assert.strictEqual(getTranslation('eligibleTitle', 'hi'), 'पात्र (ELIGIBLE)');

    // Regional languages return native localized strings
    assert.strictEqual(getTranslation('tabHome', 'ta'), 'முகப்பு');
    assert.strictEqual(getTranslation('tabHome', 'te'), 'హోమ్');

    // Unknown language fallback falls back cleanly to English
    assert.strictEqual(getTranslation('tabHome', 'fr'), 'Home');
    assert.strictEqual(getTranslation('tabHome', 'xyz'), 'Home');
  });
});

