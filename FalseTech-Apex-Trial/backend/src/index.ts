export interface Env {
  TRN_API_KEY: string;
  ALLOWED_ORIGINS?: string;
}

type PlatformKey = 'origin' | 'xbl' | 'psn';
type CacheBucket = 'search' | 'profile' | 'sessions' | 'segments';
type ProviderId = 'tracker' | 'mozambique' | 'mock';
type ProviderAttemptStatus = 'hit' | 'failed' | 'skipped' | 'blocked';
type RuntimeStatus = 'live' | 'fallback' | 'error';

type ProviderAttempt = {
  provider: ProviderId;
  status: ProviderAttemptStatus;
  code?: string;
  message?: string;
};

type StandardApiResponse<T> = {
  ok: boolean;
  source: ProviderId;
  provider?: ProviderId;
  fallbackUsed: boolean;
  cached: boolean;
  status: RuntimeStatus;
  message: string;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
  meta: {
    path: string;
    platform?: string;
    player?: string;
    query?: string;
    segmentType?: string;
    fetchedAt: string;
    provider?: ProviderId;
    fallbackUsed?: boolean;
    status?: RuntimeStatus;
    message?: string;
    providerChain?: ProviderAttempt[];
  };
};

const TRACKER_API_BASE = 'https://public-api.tracker.gg/v2/apex/standard';
const TRACKER_TIMEOUT_MS = 6500;
const TRACKER_AUTH_FALLBACK_MESSAGE = 'Tracker API access is pending approval or denied. Using local beta preview data.';
const TRACKER_UPSTREAM_FALLBACK_MESSAGE = 'Local backend reached the Worker, but Tracker upstream is unavailable. Using local beta preview data.';
const VALID_PLATFORMS = new Set<PlatformKey>(['origin', 'xbl', 'psn']);
const HANDLE_PATTERN = /^[A-Za-z0-9 _\-.\[\]\(\)~]{1,64}$/;
const SEGMENT_PATTERN = /^[a-z0-9_-]{1,32}$/i;
const SEARCH_PATTERN = /^[A-Za-z0-9 _\-.\[\]\(\)~]{1,64}$/;
const CACHE_TTL: Record<CacheBucket, number> = {
  search: 45,
  profile: 90,
  sessions: 90,
  segments: 120
};

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(request, env) });
    }

    if (request.method !== 'GET') {
      return errorResponse(request, env, 405, 'METHOD_NOT_ALLOWED', 'Method not allowed', {
        path: url.pathname,
        fetchedAt: new Date().toISOString()
      });
    }

    if (url.pathname === '/health') {
      return jsonResponse(request, env, 200, {
        ok: true,
        source: 'tracker',
        provider: 'tracker',
        fallbackUsed: false,
        cached: false,
        status: 'live',
        message: 'Apex Dashboard Worker is healthy.',
        data: {
          service: 'falsetech-apex-tracker-proxy',
          trackerConfigured: Boolean(env.TRN_API_KEY),
          providers: providerStatus(env),
          now: new Date().toISOString()
        },
        meta: { path: url.pathname, fetchedAt: new Date().toISOString() }
      });
    }

    if (!isOriginAllowed(request, env)) {
      return errorResponse(request, env, 403, 'ORIGIN_NOT_ALLOWED', 'Origin not allowed', {
        path: url.pathname,
        fetchedAt: new Date().toISOString()
      });
    }

    if (url.pathname === '/api/apex/search') {
      return handleSearch(request, env, ctx, url);
    }

    const match = url.pathname.match(/^\/api\/apex\/profile\/([^/]+)\/([^/]+)(?:\/(sessions|segments\/[^/]+))?$/);
    if (!match) {
      return errorResponse(request, env, 404, 'NOT_FOUND', 'Route not found', { path: url.pathname, fetchedAt: new Date().toISOString() });
    }

    const [, rawPlatform, rawPlayer, tail] = match;
    const platform = normalizePlatform(rawPlatform);
    const player = normalizePlayer(decodeURIComponent(rawPlayer));

    if (!platform) {
      return errorResponse(request, env, 400, 'INVALID_PLATFORM', 'Invalid platform. Use origin, xbl, or psn.', {
        path: url.pathname,
        platform: rawPlatform,
        fetchedAt: new Date().toISOString()
      });
    }

    if (!player) {
      return errorResponse(request, env, 400, 'INVALID_PLAYER', 'Invalid player handle.', {
        path: url.pathname,
        platform,
        player: rawPlayer,
        fetchedAt: new Date().toISOString()
      });
    }

    if (!tail) {
      return providerRoute({
        request,
        env,
        ctx,
        cacheBucket: 'profile',
        cacheKeyPath: url.pathname,
        providerRequest: {
          routeKind: 'profile',
          trackerPath: `/profile/${platform}/${encodeURIComponent(player)}`,
          platform,
          player
        },
        meta: { path: url.pathname, platform, player, fetchedAt: new Date().toISOString() }
      });
    }

    if (tail === 'sessions') {
      return providerRoute({
        request,
        env,
        ctx,
        cacheBucket: 'sessions',
        cacheKeyPath: url.pathname,
        providerRequest: {
          routeKind: 'sessions',
          trackerPath: `/profile/${platform}/${encodeURIComponent(player)}/sessions`,
          platform,
          player
        },
        meta: { path: url.pathname, platform, player, fetchedAt: new Date().toISOString() }
      });
    }

    if (tail.startsWith('segments/')) {
      const segmentType = normalizeSegmentType(tail.replace('segments/', ''));
      if (!segmentType) {
        return errorResponse(request, env, 400, 'INVALID_SEGMENT', 'Invalid segment type.', {
          path: url.pathname,
          platform,
          player,
          segmentType: tail.replace('segments/', ''),
          fetchedAt: new Date().toISOString()
        });
      }

      return providerRoute({
        request,
        env,
        ctx,
        cacheBucket: 'segments',
        cacheKeyPath: url.pathname,
        providerRequest: {
          routeKind: 'segments',
          trackerPath: `/profile/${platform}/${encodeURIComponent(player)}/segments/${encodeURIComponent(segmentType)}`,
          platform,
          player,
          segmentType
        },
        meta: { path: url.pathname, platform, player, segmentType, fetchedAt: new Date().toISOString() }
      });
    }

    return errorResponse(request, env, 404, 'NOT_FOUND', 'Route not found', {
      path: url.pathname,
      platform,
      player,
      fetchedAt: new Date().toISOString()
    });
  }
};

async function handleSearch(request: Request, env: Env, ctx: ExecutionContext, url: URL): Promise<Response> {
  const platform = normalizePlatform(url.searchParams.get('platform'));
  const query = normalizeSearch(url.searchParams.get('query'));

  if (!platform) {
    return errorResponse(request, env, 400, 'INVALID_PLATFORM', 'Invalid platform. Use origin, xbl, or psn.', {
      path: url.pathname,
      platform: url.searchParams.get('platform') ?? undefined,
      fetchedAt: new Date().toISOString()
    });
  }

  if (!query) {
    return errorResponse(request, env, 400, 'EMPTY_QUERY', 'Search query is required.', {
      path: url.pathname,
      platform,
      fetchedAt: new Date().toISOString()
    });
  }

  return providerRoute({
    request,
    env,
    ctx,
    cacheBucket: 'search',
    cacheKeyPath: `/api/apex/search?platform=${platform}&query=${encodeURIComponent(query)}`,
    providerRequest: {
      routeKind: 'search',
      trackerPath: `/search?platform=${platform}&query=${encodeURIComponent(query)}`,
      platform,
      query
    },
    meta: {
      path: '/api/apex/search',
      platform,
      query,
      fetchedAt: new Date().toISOString()
    }
  });
}

type ProviderRouteArgs = {
  request: Request;
  env: Env;
  ctx: ExecutionContext;
  cacheBucket: CacheBucket;
  cacheKeyPath: string;
  providerRequest: ProviderRequest;
  meta: StandardApiResponse<unknown>['meta'];
};

async function providerRoute(args: ProviderRouteArgs): Promise<Response> {
  const { request, env, ctx, cacheBucket, cacheKeyPath, providerRequest, meta } = args;
  const cache = caches.default;
  const cacheKey = buildCacheKey(request, cacheKeyPath);
  const cached = await cache.match(cacheKey);

  if (cached) {
    const body = (await cached.clone().json()) as StandardApiResponse<unknown>;
    normalizeCachedBody(body);
    return jsonResponse(request, env, 200, body, {
      'Cache-Control': `public, max-age=${CACHE_TTL[cacheBucket]}`,
      'X-Proxy-Cache': 'HIT'
    });
  }

  try {
    const providerResult = await fetchProviderData(env, providerRequest);
    const payload: StandardApiResponse<unknown> = {
      ok: true,
      source: providerResult.provider,
      provider: providerResult.provider,
      fallbackUsed: providerResult.fallbackUsed,
      cached: false,
      status: providerResult.status,
      message: providerResult.message,
      data: providerResult.data,
      meta: {
        ...meta,
        provider: providerResult.provider,
        fallbackUsed: providerResult.fallbackUsed,
        status: providerResult.status,
        message: providerResult.message,
        providerChain: providerResult.attempts
      }
    };
    const response = jsonResponse(request, env, 200, payload, {
      'Cache-Control': `public, max-age=${CACHE_TTL[cacheBucket]}`,
      'X-Proxy-Cache': 'MISS'
    });
    ctx.waitUntil(cache.put(cacheKey, response.clone()));
    return response;
  } catch (error) {
    if (error instanceof ProviderChainError) {
      return errorResponse(request, env, error.status, error.code, error.message, {
        ...meta,
        provider: error.provider,
        providerChain: error.attempts
      });
    }
    return errorResponse(request, env, 502, 'TRACKER_PROXY_FAILURE', 'Tracker proxy failure', meta);
  }
}

type ProviderRequest = {
  routeKind: CacheBucket;
  trackerPath: string;
  platform: PlatformKey;
  player?: string;
  query?: string;
  segmentType?: string;
};

type ProviderResult = {
  provider: ProviderId;
  data: unknown;
  attempts: ProviderAttempt[];
  fallbackUsed: boolean;
  status: RuntimeStatus;
  message: string;
};

type ApexDataProvider = {
  id: ProviderId;
  label: string;
  configured: (env: Env) => boolean;
  fetch: (env: Env, request: ProviderRequest) => Promise<unknown>;
};

class ProviderHttpError extends Error {
  status: number;
  code: string;
  provider: ProviderId;
  terminal: boolean;

  constructor(provider: ProviderId, status: number, code: string, message: string, terminal = false) {
    super(message);
    this.name = 'ProviderHttpError';
    this.provider = provider;
    this.status = status;
    this.code = code;
    this.terminal = terminal;
  }
}

class ProviderChainError extends Error {
  status: number;
  code: string;
  provider: ProviderId;
  attempts: ProviderAttempt[];

  constructor(error: ProviderHttpError, attempts: ProviderAttempt[]) {
    super(error.message);
    this.name = 'ProviderChainError';
    this.status = error.status;
    this.code = error.code;
    this.provider = error.provider;
    this.attempts = attempts;
  }
}

const trackerProvider: ApexDataProvider = {
  id: 'tracker',
  label: 'Tracker Provider',
  configured: (env) => Boolean(env.TRN_API_KEY),
  async fetch(env, request) {
    if (!env.TRN_API_KEY) {
      throw new ProviderHttpError('tracker', 503, 'TRACKER_NOT_CONFIGURED', 'Tracker integration is not configured', true);
    }
    return fetchTracker(`${TRACKER_API_BASE}${request.trackerPath}`, env.TRN_API_KEY);
  }
};

const mozambiqueProvider: ApexDataProvider = {
  id: 'mozambique',
  label: 'Mozambique / Apex Legends Status Provider',
  configured: () => false,
  async fetch() {
    throw new ProviderHttpError(
      'mozambique',
      503,
      'FALLBACK_PROVIDER_NOT_CONFIGURED',
      'Mozambique / Apex Legends Status provider is not configured'
    );
  }
};

const mockProvider: ApexDataProvider = {
  id: 'mock',
  label: 'Mock Provider',
  configured: () => true,
  async fetch(_env, request) {
    return mockProviderData(request);
  }
};

const PROVIDERS: ApexDataProvider[] = [trackerProvider, mozambiqueProvider, mockProvider];

async function fetchProviderData(env: Env, request: ProviderRequest): Promise<ProviderResult> {
  const attempts: ProviderAttempt[] = [];
  let firstError: ProviderHttpError | null = null;

  for (const provider of PROVIDERS) {
    if (!provider.configured(env)) {
      attempts.push({
        provider: provider.id,
        status: 'skipped',
        code: 'PROVIDER_NOT_CONFIGURED',
        message: `${provider.label} is not configured`
      });
      continue;
    }

    try {
      const data = await provider.fetch(env, request);
      attempts.push({ provider: provider.id, status: 'hit' });
      const runtime = runtimeStatusFor(provider.id, attempts);
      return { provider: provider.id, data, attempts, ...runtime };
    } catch (error) {
      const providerError = normalizeProviderError(provider.id, error);
      attempts.push({
        provider: provider.id,
        status: providerError.terminal ? 'blocked' : 'failed',
        code: providerError.code,
        message: providerError.message
      });
      firstError ??= providerError;
      if (providerError.terminal) break;
    }
  }

  throw new ProviderChainError(
    firstError ?? new ProviderHttpError('tracker', 502, 'PROVIDER_CHAIN_FAILURE', 'Provider chain failure'),
    attempts
  );
}

function normalizeProviderError(provider: ProviderId, error: unknown): ProviderHttpError {
  if (error instanceof ProviderHttpError) return error;
  if (error instanceof Error) {
    return new ProviderHttpError(provider, 502, 'PROVIDER_FAILURE', 'Provider failure');
  }
  return new ProviderHttpError(provider, 502, 'PROVIDER_FAILURE', 'Provider failure');
}

function runtimeStatusFor(provider: ProviderId, attempts: ProviderAttempt[]): Pick<ProviderResult, 'fallbackUsed' | 'status' | 'message'> {
  const fallbackUsed = provider !== 'tracker' || attempts.some((attempt) => attempt.provider === 'tracker' && attempt.status !== 'hit');
  if (!fallbackUsed) {
    return {
      fallbackUsed: false,
      status: 'live',
      message: 'Live Tracker data loaded.'
    };
  }

  const trackerAttempt = attempts.find((attempt) => attempt.provider === 'tracker' && attempt.status !== 'hit');
  if (trackerAttempt?.code === 'UNAUTHORIZED' || trackerAttempt?.code === 'FORBIDDEN') {
    return {
      fallbackUsed: true,
      status: 'fallback',
      message: TRACKER_AUTH_FALLBACK_MESSAGE
    };
  }

  if (
    trackerAttempt?.code === 'TRACKER_UPSTREAM_UNAVAILABLE' ||
    trackerAttempt?.code === 'TRACKER_TIMEOUT' ||
    trackerAttempt?.code === 'TRACKER_PROXY_FAILURE' ||
    trackerAttempt?.code === 'PROVIDER_FAILURE'
  ) {
    return {
      fallbackUsed: true,
      status: 'fallback',
      message: TRACKER_UPSTREAM_FALLBACK_MESSAGE
    };
  }

  if (trackerAttempt?.code === 'RATE_LIMITED') {
    return {
      fallbackUsed: true,
      status: 'fallback',
      message: 'Tracker rate limit reached. Using local beta preview data.'
    };
  }

  if (trackerAttempt?.status === 'skipped' || trackerAttempt?.code === 'PROVIDER_NOT_CONFIGURED') {
    return {
      fallbackUsed: true,
      status: 'fallback',
      message: 'Tracker integration is not configured. Using local beta preview data.'
    };
  }

  return {
    fallbackUsed: true,
    status: 'fallback',
    message: 'Live Tracker data is unavailable. Using local beta preview data.'
  };
}

function providerStatus(env: Env) {
  return PROVIDERS.map((provider, index) => ({
    id: provider.id,
    label: provider.label,
    priority: index + 1,
    configured: provider.configured(env)
  }));
}

async function fetchTracker(url: string, apiKey: string): Promise<unknown> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TRACKER_TIMEOUT_MS);
  let response: Response;

  try {
    response = await fetch(url, {
      headers: {
        Accept: 'application/json',
        'TRN-Api-Key': apiKey,
        'User-Agent': 'FalseTech-Apex-Proxy/1.0'
      },
      signal: controller.signal,
      cf: {
        cacheEverything: false,
        cacheTtl: 30
      }
    });
  } catch (error) {
    if (isAbortError(error)) {
      throw new ProviderHttpError('tracker', 502, 'TRACKER_TIMEOUT', 'Tracker request timed out');
    }
    throw new ProviderHttpError('tracker', 502, 'TRACKER_UPSTREAM_UNAVAILABLE', 'Tracker upstream is unavailable');
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    throw mapUpstreamError('tracker', response.status);
  }

  return response.json();
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException ? error.name === 'AbortError' : error instanceof Error && error.name === 'AbortError';
}

function mapUpstreamError(provider: ProviderId, status: number): ProviderHttpError {
  switch (status) {
    case 400:
      return new ProviderHttpError(provider, 400, 'BAD_REQUEST', 'Bad request to Tracker', true);
    case 401:
      return new ProviderHttpError(provider, 401, 'UNAUTHORIZED', TRACKER_AUTH_FALLBACK_MESSAGE);
    case 403:
      return new ProviderHttpError(provider, 403, 'FORBIDDEN', TRACKER_AUTH_FALLBACK_MESSAGE);
    case 404:
      return new ProviderHttpError(provider, 404, 'PLAYER_NOT_FOUND', 'Player not found', true);
    case 429:
      return new ProviderHttpError(provider, 429, 'RATE_LIMITED', 'Tracker rate limit reached');
    default:
      return new ProviderHttpError(provider, 502, 'TRACKER_UPSTREAM_UNAVAILABLE', TRACKER_UPSTREAM_FALLBACK_MESSAGE);
  }
}

function normalizeCachedBody(body: StandardApiResponse<unknown>): void {
  body.cached = true;
  body.provider ??= body.meta.provider ?? body.source;
  body.fallbackUsed ??= body.meta.fallbackUsed ?? body.provider !== 'tracker';
  body.status ??= body.meta.status ?? (body.fallbackUsed ? 'fallback' : 'live');
  body.message ??= body.meta.message ?? (body.fallbackUsed ? 'Live Tracker data is unavailable. Using local beta preview data.' : 'Live Tracker data loaded.');
  body.meta = {
    ...body.meta,
    provider: body.provider,
    fallbackUsed: body.fallbackUsed,
    status: body.status,
    message: body.message
  };
}

function mockProviderData(request: ProviderRequest): unknown {
  switch (request.routeKind) {
    case 'search':
      return [
        {
          platformSlug: request.platform,
          platformUserHandle: request.query ?? request.player ?? 'NotFalsetto'
        }
      ];
    case 'profile':
      return {
        data: {
          platformInfo: {
            platformSlug: request.platform,
            platformUserHandle: request.player ?? 'NotFalsetto'
          },
          metadata: { activeLegendName: 'Lifeline' },
          segments: [
            {
              type: 'overview',
              stats: {
                level: { value: 894, displayValue: '894' },
                rankScore: { value: 12350, displayValue: 'Diamond 4', metadata: { rankName: 'Diamond 4' } },
                matchesPlayed: { value: 1050, displayValue: '1,050' },
                kills: { value: 2646, displayValue: '2,646' },
                damage: { value: 1893101, displayValue: '1,893,101' },
                wins: { value: 68, displayValue: '68' }
              }
            }
          ]
        }
      };
    case 'sessions':
      return {
        data: {
          items: [
            {
              metadata: { legendName: 'Horizon', mapName: 'Olympus', timestamp: 'Preview session' },
              stats: {
                placement: { displayValue: '#4' },
                rankPoints: { value: 45, displayValue: '+45' },
                kills: { value: 5, displayValue: '5' },
                damage: { value: 1481, displayValue: '1,481' }
              }
            }
          ]
        }
      };
    case 'segments':
      return {
        data: {
          segments: [
            {
              type: request.segmentType ?? 'legend',
              metadata: { name: 'Lifeline', roleName: 'Support' },
              stats: {
                kills: { value: 1293, displayValue: '1,293' },
                damage: { value: 1274677, displayValue: '1,274,677' },
                wins: { value: 66, displayValue: '66' }
              }
            },
            {
              type: request.segmentType ?? 'legend',
              metadata: { name: 'Horizon', roleName: 'Skirmisher' },
              stats: {
                kills: { value: 842, displayValue: '842' },
                damage: { value: 618420, displayValue: '618,420' },
                wins: { value: 32, displayValue: '32' }
              }
            }
          ]
        }
      };
  }
}

function normalizePlatform(value: string | null): PlatformKey | null {
  if (!value) return null;
  const candidate = value.trim().toLowerCase() as PlatformKey;
  return VALID_PLATFORMS.has(candidate) ? candidate : null;
}

function normalizePlayer(value: string | null): string | null {
  if (!value) return null;
  const candidate = value.trim();
  return candidate && HANDLE_PATTERN.test(candidate) ? candidate : null;
}

function normalizeSearch(value: string | null): string | null {
  if (!value) return null;
  const candidate = value.trim();
  return candidate && SEARCH_PATTERN.test(candidate) ? candidate : null;
}

function normalizeSegmentType(value: string | null): string | null {
  if (!value) return null;
  const candidate = value.trim().toLowerCase();
  return candidate && SEGMENT_PATTERN.test(candidate) ? candidate : null;
}

function buildCacheKey(request: Request, path: string): Request {
  const url = new URL(request.url);
  return new Request(`${url.origin}${path}`, { method: 'GET' });
}

function allowedOrigins(env: Env): string[] {
  return (env.ALLOWED_ORIGINS ?? '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function isOriginAllowed(request: Request, env: Env): boolean {
  const origin = request.headers.get('Origin');
  const allowed = allowedOrigins(env);
  if (!origin) return true;
  if (!allowed.length) return true;
  return allowed.includes(origin);
}

function corsHeaders(request: Request, env: Env): HeadersInit {
  const origin = request.headers.get('Origin');
  const allowed = allowedOrigins(env);
  const allowOrigin = !origin ? '*' : allowed.length === 0 ? origin : allowed.includes(origin) ? origin : 'null';

  return {
    'Access-Control-Allow-Origin': allowOrigin,
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin'
  };
}

function withCors(response: Response, request: Request, env: Env): Response {
  const next = new Response(response.body, response);
  const headers = corsHeaders(request, env);
  for (const [key, value] of Object.entries(headers)) {
    next.headers.set(key, value);
  }
  return next;
}

function jsonResponse<T>(request: Request, env: Env, status: number, body: StandardApiResponse<T> | Record<string, unknown>, extraHeaders: HeadersInit = {}): Response {
  const response = new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      ...extraHeaders
    }
  });
  return withCors(response, request, env);
}

function errorResponse(
  request: Request,
  env: Env,
  status: number,
  code: string,
  message: string,
  meta: StandardApiResponse<never>['meta']
): Response {
  const body: StandardApiResponse<never> = {
    ok: false,
    source: meta.provider ?? 'tracker',
    provider: meta.provider ?? 'tracker',
    fallbackUsed: false,
    cached: false,
    status: 'error',
    message,
    error: { code, message },
    meta: {
      ...meta,
      fallbackUsed: false,
      status: 'error',
      message
    }
  };

  return jsonResponse(request, env, status, body, {
    'Cache-Control': 'no-store',
    'X-Proxy-Cache': 'BYPASS'
  });
}
