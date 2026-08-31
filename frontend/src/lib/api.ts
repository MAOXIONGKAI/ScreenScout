import {
  MoviesResponse,
  MovieDetail,
  Cinema,
  AuthResponse,
  LoginPayload,
  RegisterPayload,
  User,
  NotificationChannel,
  Subscription,
  Review,
  CreateReviewPayload,
  MovieReviewsResponse,
  AdminStatsResponse,
  ScrapeResponse,
  CleanResponse,
} from "./types";

const API_BASE =
  typeof window !== "undefined"
    ? ""
    : process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

interface FetchMoviesParams {
  provider?: string;
  branch?: string;
  status?: string;
  search?: string;
  time_from?: string;
  time_to?: string;
  page?: number;
  limit?: number;
}

export async function fetchMovies(
  params: FetchMoviesParams = {}
): Promise<MoviesResponse> {
  const searchParams = new URLSearchParams();

  if (params.provider) searchParams.set("provider", params.provider);
  if (params.branch) searchParams.set("branch", params.branch);
  if (params.status) searchParams.set("status", params.status);
  if (params.search) searchParams.set("search", params.search);
  if (params.time_from) searchParams.set("time_from", params.time_from);
  if (params.time_to) searchParams.set("time_to", params.time_to);
  if (params.page) searchParams.set("page", params.page.toString());
  if (params.limit) searchParams.set("limit", params.limit.toString());

  const res = await fetch(`${API_BASE}/api/movies?${searchParams.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch movies");
  return res.json();
}

export async function fetchMovieById(id: number): Promise<MovieDetail> {
  const res = await fetch(`${API_BASE}/api/movies/${id}`);
  if (!res.ok) throw new Error("Failed to fetch movie");
  return res.json();
}

export async function fetchCinemas(provider?: string): Promise<Cinema[]> {
  const searchParams = new URLSearchParams();
  if (provider) searchParams.set("provider", provider);

  const res = await fetch(`${API_BASE}/api/cinemas?${searchParams.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch cinemas");
  return res.json();
}

export async function fetchProviders(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/providers`);
  if (!res.ok) throw new Error("Failed to fetch providers");
  return res.json();
}

export async function registerUser(
  payload: RegisterPayload
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Registration failed");
  }
  return data;
}

export async function loginUser(
  payload: LoginPayload
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Login failed");
  }
  return data;
}

export async function fetchCurrentUser(token: string): Promise<User> {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Session expired");
  }
  return data;
}

// Notification Channel API
export async function fetchNotificationChannel(
  token: string
): Promise<NotificationChannel | null> {
  const res = await fetch(`${API_BASE}/api/user/notification-channel`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Failed to fetch notification channel");
  }
  return data.channel;
}

export async function saveNotificationChannel(
  token: string,
  channelUserId: string
): Promise<NotificationChannel> {
  const res = await fetch(`${API_BASE}/api/user/notification-channel`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      channel_type: "TELEGRAM",
      channel_user_id: channelUserId,
    }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Failed to save notification handle");
  }
  return data;
}

export async function testNotificationChannel(
  token: string
): Promise<{ success: boolean; status?: string; message?: string; error?: string; hint?: string }> {
  const res = await fetch(`${API_BASE}/api/user/notification-channel/test`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();
  if (!res.ok && !data.error) {
    throw new Error("Failed to dispatch test notification");
  }
  return data;
}

// Subscriptions API
export async function fetchSubscriptions(
  token: string
): Promise<Subscription[]> {
  const res = await fetch(`${API_BASE}/api/subscriptions`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Failed to fetch subscriptions");
  }
  return data.subscriptions || [];
}

export async function createSubscription(
  token: string,
  movieQuery: string
): Promise<Subscription> {
  const res = await fetch(`${API_BASE}/api/subscriptions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ movie_query: movieQuery }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Failed to create subscription");
  }
  return data;
}

export async function deleteSubscription(
  token: string,
  id: number
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/subscriptions/${id}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.error || "Failed to delete subscription");
  }
}

export async function toggleSubscription(
  token: string,
  id: number
): Promise<Subscription> {
  const res = await fetch(`${API_BASE}/api/subscriptions/${id}/toggle`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Failed to toggle subscription");
  }
  return data;
}

// Movie Reviews API
export async function fetchMovieReviews(
  movieId: number,
  page: number = 1,
  limit: number = 5,
  rating: number = 0,
  sort: string = "newest"
): Promise<MovieReviewsResponse> {
  const params = new URLSearchParams();
  if (page) params.append("page", page.toString());
  if (limit) params.append("limit", limit.toString());
  if (rating && rating >= 1 && rating <= 5) {
    params.append("rating", rating.toString());
  }
  if (sort && sort !== "newest") {
    params.append("sort", sort);
  }

  const query = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/api/movies/${movieId}/reviews${query}`);
  if (!res.ok) {
    throw new Error("Failed to fetch movie reviews");
  }
  return res.json();
}

export async function submitMovieReview(
  token: string,
  movieId: number,
  payload: CreateReviewPayload
): Promise<Review> {
  const res = await fetch(`${API_BASE}/api/movies/${movieId}/reviews`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Failed to submit review");
  }
  return data;
}

export async function deleteMovieReview(
  token: string,
  movieId: number,
  reviewId: number
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/movies/${movieId}/reviews/${reviewId}`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.error || "Failed to delete review");
  }
}

// fetchAdminStats fetches platform metrics for administrators (GET /api/admin/stats)
export async function fetchAdminStats(token: string): Promise<AdminStatsResponse> {
  const res = await fetch(`${API_BASE}/api/admin/stats`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Failed to fetch admin statistics");
  }
  return data;
}

// invalidateAllMovieCache triggers server-side Redis cache purge (POST /api/cache/movies/invalidate)
export async function invalidateAllMovieCache(token?: string): Promise<{ flushed_count: number; message: string }> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/api/cache/movies/invalidate`, {
    method: "POST",
    headers,
    body: JSON.stringify({}),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Failed to invalidate cache");
  }
  return data;
}

// triggerSubscriptionCheck triggers matching pass across active subscriptions (POST /api/subscriptions/check)
export async function triggerSubscriptionCheck(): Promise<{ message: string; matches_found: number }> {
  const res = await fetch(`${API_BASE}/api/subscriptions/check`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Failed to trigger subscription check");
  }
  return data;
}

// triggerAdminScrape triggers full scrape of cinemas, movies, and schedules (POST /api/admin/scrape)
export async function triggerAdminScrape(token: string): Promise<ScrapeResponse> {
  const res = await fetch(`${API_BASE}/api/admin/scrape`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({}),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || data.details || "Failed to trigger refetch of cinemas, movies, and schedules");
  }
  return data;
}

// triggerAdminClean triggers database cleanup of past schedules and outdated movies (POST /api/admin/clean)
export async function triggerAdminClean(token: string): Promise<CleanResponse> {
  const res = await fetch(`${API_BASE}/api/admin/clean`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({}),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || data.details || "Failed to trigger database cleanup");
  }
  return data;
}



