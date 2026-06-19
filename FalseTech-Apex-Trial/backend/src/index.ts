export interface Env {
  TRN_API_KEY: string;
  ALLOWED_ORIGINS?: string;
}

type PlatformKey = 'origin' | 'xbl' | 'psn';
type CacheBucket = 'search' | 'profile' | 'sessions' | 'segments';

type StandardApiResponse<T> = {
  ok: boolean;
  source: 'tracker';
  cached: boolean;
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
  };
};

const API_BASE = 'https://public-api.tracker.gg/v2/apex/standard';
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
      return errorResponse(request, env, 405, 'METHOD_NOT_ALLOWED', 'Method not allowed', { path: url.pathname });
    }

    if (!env.TRN_API_KEY) {
      return errorResponse(request, env, 500, 'MISSING_API_KEY', 'Server missing TRN_API_KEY', { path: url.pathname });
    }

    if (!isOriginAllowed(request, env)) {
      return errorResponse(request, env, 403, 'ORIGIN_NOT_ALLOWED', 'Origin not allowed', { path: url.pathname });
    }

    if (url.pathname === '/health') {
      return jsonResponse(request, env, 200, {
        ok: true,
        source: 'tracker',
        cached: false,
        data: {
          service: 'falsetech-apex-tracker-proxy',
          now: new Date().toISOString()
        },
        meta: { path: url.pathname, fetchedAt: new Date().toISOString() }
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
      return proxyRoute({
        request,
        env,
        ctx,
        cacheBucket: 'profile',
        cacheKeyPath: url.pathname,
        upstreamUrl: `${API_BASE}/profile/${platform}/${encodeURIComponent(player)}`,
        meta: { path: url.pathname, platform, player, fetchedAt: new Date().toISOString() }
      });
    }

    if (tail === 'sessions') {
      return proxyRoute({
        request,
        env,
        ctx,
        cacheBucket: 'sessions',
        cacheKeyPath: url.pathname,
        upstreamUrl: `${API_BASE}/profile/${platform}/${encodeURIComponent(player)}/sessions`,
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

      return proxyRoute({
        request,
        env,
        ctx,
        cacheBucket: 'segments',
        cacheKeyPath: url.pathname,
        upstreamUrl: `${API_BASE}/profile/${platform}/${encodeURIComponent(player)}/segments/${encodeURIComponent(segmentType)}`,
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

  return proxyRoute({
    request,
    env,
    ctx,
    cacheBucket: 'search',
    cacheKeyPath: `/api/apex/search?platform=${platform}&query=${encodeURIComponent(query)}`,
    upstreamUrl: `${API_BASE}/search?platform=${platform}&query=${encodeURIComponent(query)}`,
    meta: {
      path: '/api/apex/search',
      platform,
      query,
      fetchedAt: new Date().toISOString()
    }
  });
}

type ProxyRouteArgs = {
  request: Request;
  env: Env;
  ctx: ExecutionContext;
  cacheBucket: CacheBucket;
  cacheKeyPath: string;
  upstreamUrl: string;
  meta: StandardApiResponse<unknown>['meta'];
};

async function proxyRoute(args: ProxyRouteArgs): Promise<Response> {
  const { request, env, ctx, cacheBucket, cacheKeyPath, upstreamUrl, meta } = args;
  const cache = caches.default;
  const cacheKey = buildCacheKey(request, cacheKeyPath);
  const cached = await cache.match(cacheKey);

  if (cached) {
    const body = (await cached.clone().json()) as StandardApiResponse<unknown>;
    body.cached = true;
    return jsonResponse(request, env, 200, body, {
      'Cache-Control': `public, max-age=${CACHE_TTL[cacheBucket]}`,
      'X-Proxy-Cache': 'HIT'
    });
  }

  try {
    const upstream = await fetchTracker(upstreamUrl, env.TRN_API_KEY);
    const payload: StandardApiResponse<unknown> = {
      ok: true,
      source: 'tracker',
      cached: false,
      data: upstream,
      meta
    };
    const response = jsonResponse(request, env, 200, payload, {
      'Cache-Control': `public, max-age=${CACHE_TTL[cacheBucket]}`,
      'X-Proxy-Cache': 'MISS'
    });
    ctx.waitUntil(cache.put(cacheKey, response.clone()));
    return response;
  } catch (error) {
    if (error instanceof TrackerHttpError) {
      return errorResponse(request, env, error.status, error.code, error.message, meta);
    }
    return errorResponse(request, env, 502, 'TRACKER_PROXY_FAILURE', 'Tracker proxy failure', meta);
  }
}

class TrackerHttpError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function fetchTracker(url: string, apiKey: string): Promise<unknown> {
  const response = await fetch(url, {
    headers: {
      Accept: 'application/json',
      'TRN-Api-Key': apiKey,
      'User-Agent': 'FalseTech-Apex-Proxy/1.0'
    },
    cf: {
      cacheEverything: false,
      cacheTtl: 30
    }
  });

  if (!response.ok) {
    throw mapUpstreamError(response.status);
  }

  return response.json();
}

function mapUpstreamError(status: number): TrackerHttpError {
  switch (status) {
    case 400:
      return new TrackerHttpError(400, 'BAD_REQUEST', 'Bad request to Tracker');
    case 401:
      return new TrackerHttpError(401, 'UNAUTHORIZED', 'Unauthorized upstream request');
    case 403:
      return new TrackerHttpError(403, 'FORBIDDEN', 'Tracker access forbidden');
    case 404:
      return new TrackerHttpError(404, 'PLAYER_NOT_FOUND', 'Player not found');
    case 429:
      return new TrackerHttpError(429, 'RATE_LIMITED', 'Tracker rate limit reached');
    default:
      return new TrackerHttpError(502, 'TRACKER_PROXY_FAILURE', 'Tracker proxy failure');
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
    source: 'tracker',
    cached: false,
    error: { code, message },
    meta
  };

  return jsonResponse(request, env, status, body, {
    'Cache-Control': 'no-store',
    'X-Proxy-Cache': 'BYPASS'
  });
}
