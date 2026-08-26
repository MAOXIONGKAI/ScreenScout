import { MoviesResponse, MovieDetail, Cinema } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

interface FetchMoviesParams {
  provider?: string;
  branch?: string;
  status?: string;
  search?: string;
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
