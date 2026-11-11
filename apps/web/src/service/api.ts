
const API_BASE_URL = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const API_PREFIX = "/api/v1";

export interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  expires_in: number;
  user: User;
}

export interface MessageResponse {
  message: string;
}

export interface MarketDataResponse {
  symbol: string;
  timeframe: string;
  count: number;
  candles: unknown[];
}

export interface AIAnalysisResponse {
  success: boolean;
  provider: string;
  model: string;
  interpretation: {
    market_bias: string;
    confidence: string;
    summary: string;
    bullish_scenario: Record<string, unknown>;
    bearish_scenario: Record<string, unknown>;
    key_levels_and_zones: unknown[];
    risk_factors: string[];
    conflicting_evidence: string[];
    analyst_recommendation: string;
    human_confirmation_required: boolean;
  };
  execution_enabled: boolean;
  human_confirmation_required: boolean;
}

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(
      typeof detail === "string"
        ? detail
        : "An API request failed."
    );

    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  retry = true
): Promise<T> {
  const headers = new Headers(options.headers);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(
    `${API_BASE_URL}${endpoint}`,
    {
      ...options,
      headers,
      credentials: "include",
    }
  );

  if (
    response.status === 401 &&
    retry &&
    !endpoint.endsWith("/auth/refresh") &&
    !endpoint.endsWith("/auth/login")
  ) {
    const refreshed = await refreshAccessToken();

    if (refreshed) {
      return request<T>(endpoint, options, false);
    }

    setAccessToken(null);
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      data?.detail || data?.message || "Request failed."
    );
  }

  return data as T;
}

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const result = await request<TokenResponse>(
        `${API_PREFIX}/auth/refresh`,
        { method: "POST" },
        false
      );

      setAccessToken(result.access_token);
      return result.access_token;
    } catch {
      setAccessToken(null);
      return null;
    }
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

// AUTHENTICATION

export const authAPI = {
  login: (email: string, password: string) =>
    request<TokenResponse>(`${API_PREFIX}/auth/login`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }).then((result) => {
      setAccessToken(result.access_token);
      return result;
    }),

  me: () =>
    request<User>(`${API_PREFIX}/auth/me`),

  refresh: refreshAccessToken,

  logout: async () => {
    try {
      return await request<MessageResponse>(
        `${API_PREFIX}/auth/logout`,
        { method: "POST" },
        false
      );
    } finally {
      setAccessToken(null);
    }
  },

  forgotPassword: (email: string) =>
    request<MessageResponse>(
      `${API_PREFIX}/auth/forgot-password`,
      {
        method: "POST",
        body: JSON.stringify({ email }),
      },
      false
    ),

  resetPassword: (token: string, new_password: string) =>
    request<MessageResponse>(
      `${API_PREFIX}/auth/reset-password`,
      {
        method: "POST",
        body: JSON.stringify({ token, new_password }),
      },
      false
    ),
};

// MARKET DATA

export const marketAPI = {
  latest: (
    symbol: string,
    timeframe: string,
    limit = 500
  ) => {
    const params = new URLSearchParams({
      symbol,
      timeframe,
      limit: String(limit),
    });

    return request<MarketDataResponse>(
      `${API_PREFIX}/market-data/latest?${params}`
    );
  },
};

// TECHNICAL ANALYSIS

export const analysisAPI = {
  indicators: (
    symbol: string,
    timeframe: string,
    limit = 500
  ) => {
    const params = new URLSearchParams({
      symbol,
      timeframe,
      limit: String(limit),
    });

    return request(
      `${API_PREFIX}/analysis/indicators?${params}`
    );
  },

  unified: (
    symbol: string,
    timeframe: string,
    limit = 500
  ) => {
    const params = new URLSearchParams({
      symbol,
      timeframe,
      limit: String(limit),
    });

    return request(
      `${API_PREFIX}/analysis/unified?${params}`
    );
  },

  multiTimeframe: (symbol: string, limit = 500) => {
    const params = new URLSearchParams({
      symbol,
      limit: String(limit),
    });

    return request(
      `${API_PREFIX}/analysis/multi-timeframe?${params}`
    );
  },

  ai: (
    market_analysis: Record<string, unknown>,
    multi_timeframe_analysis?: Record<string, unknown> | null
  ) =>
    request<AIAnalysisResponse>(
      `${API_PREFIX}/analysis/ai`,
      {
        method: "POST",
        body: JSON.stringify({
          market_analysis,
          multi_timeframe_analysis:
            multi_timeframe_analysis || null,
        }),
      }
    ),
};

export interface AnalysisHistoryItem {
  id: string;
  symbol: string;
  timeframe: string;
  analyzed_at: string;
  directional_bias: "bullish" | "bearish" | "neutral" | "uncertain";
  confidence: "low" | "medium" | "high";
  summary: string;
  human_confirmation_required: boolean;
}

export interface AnalysisHistoryRecord extends AnalysisHistoryItem {
  user_id: string;
  market_analysis: Record<string, unknown>;
  multi_timeframe_analysis: Record<string, unknown> | null;
  ai_result: {
    success: boolean;
    provider?: string;
    model?: string;
    interpretation: {
      market_bias: string;
      confidence: string;
      summary: string;
      bullish_scenario: {
        conditions: unknown[];
        supporting_evidence: unknown[];
        invalidation: unknown[];
      };
      bearish_scenario: {
        conditions: unknown[];
        supporting_evidence: unknown[];
        invalidation: unknown[];
      };
      key_levels_and_zones: unknown[];
      risk_factors: unknown[];
      conflicting_evidence: unknown[];
      analyst_recommendation: string;
      human_confirmation_required: boolean;
    };
    execution_enabled: boolean;
    human_confirmation_required: boolean;
  };
  execution_enabled: boolean;
}

export interface AnalysisHistoryListResponse {
  success: boolean;
  items: AnalysisHistoryItem[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}

export interface AnalysisHistoryDetailResponse {
  success: boolean;
  record: AnalysisHistoryRecord;
}

export interface AnalysisHistoryFilters {
  symbol?: string;
  timeframe?: string;
  bias?: string;
  search?: string;
  page?: number;
  limit?: number;
}

export const analysisHistoryAPI = {
  list: (filters: AnalysisHistoryFilters = {}) => {
    const params = new URLSearchParams();

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        params.set(key, String(value));
      }
    });

    const query = params.toString();

    return request<AnalysisHistoryListResponse>(
      `/analysis/history${query ? `?${query}` : ""}`
    );
  },

  detail: (id: string) =>
    request<AnalysisHistoryDetailResponse>(
      `/analysis/history/${encodeURIComponent(id)}`
    ),
};

export { ApiError };
