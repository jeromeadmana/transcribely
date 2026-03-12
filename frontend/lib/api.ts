const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiResponse<T> {
  data?: T;
  error?: string;
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return { error: errorData.detail || `HTTP ${response.status}` };
    }

    const data = await response.json();
    return { data };
  } catch (error) {
    return { error: error instanceof Error ? error.message : "Network error" };
  }
}

// Auth
export interface User {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export async function register(email: string, password: string, name?: string) {
  return fetchApi<TokenResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
}

export async function login(email: string, password: string) {
  return fetchApi<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function refreshToken(refresh_token: string) {
  return fetchApi<TokenResponse>("/api/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token }),
  });
}

export async function getMe() {
  return fetchApi<User>("/api/auth/me");
}

// Videos
export interface Video {
  id: string;
  organization_id: string;
  uploaded_by: string | null;
  title: string | null;
  original_filename: string | null;
  storage_key: string;
  duration_seconds: number | null;
  file_size_bytes: number | null;
  mime_type: string | null;
  status: string;
  error_message: string | null;
  progress: number;
  created_at: string;
  updated_at: string;
}

export async function uploadVideo(
  file: File,
  title?: string,
  onProgress?: (progress: number) => void
): Promise<ApiResponse<Video>> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);
    if (title) {
      formData.append("title", title);
    }

    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && onProgress) {
        const progress = Math.round((event.loaded / event.total) * 100);
        onProgress(progress);
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          resolve({ data });
        } catch {
          resolve({ error: "Invalid response" });
        }
      } else {
        try {
          const errorData = JSON.parse(xhr.responseText);
          resolve({ error: errorData.detail || `HTTP ${xhr.status}` });
        } catch {
          resolve({ error: `HTTP ${xhr.status}` });
        }
      }
    });

    xhr.addEventListener("error", () => {
      resolve({ error: "Upload failed - network error" });
    });

    xhr.open("POST", `${API_URL}/api/videos/upload`);
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }
    xhr.send(formData);
  });
}

export async function listVideos(skip = 0, limit = 50) {
  return fetchApi<Video[]>(`/api/videos?skip=${skip}&limit=${limit}`);
}

export async function getVideo(video_id: string) {
  return fetchApi<Video & { transcript?: Transcript }>(`/api/videos/${video_id}`);
}

export async function deleteVideo(video_id: string) {
  return fetchApi<void>(`/api/videos/${video_id}`, { method: "DELETE" });
}

// Transcripts
export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  speaker: string | null;
}

export interface Transcript {
  id: string;
  video_id: string;
  full_text: string | null;
  segments: TranscriptSegment[] | null;
  language: string | null;
  word_count: number | null;
  created_at: string;
  updated_at: string;
}

export async function getTranscript(video_id: string) {
  return fetchApi<Transcript>(`/api/transcripts/${video_id}`);
}

export async function exportTranscript(video_id: string, format: "txt" | "json" | "srt" | "vtt") {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const response = await fetch(`${API_URL}/api/transcripts/${video_id}/export?format=${format}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  return response;
}

// Billing & Usage
export interface UsageStats {
  plan: string;
  limit_minutes: number | null;
  used_minutes: number;
  remaining_minutes: number | null;
  percentage_used: number;
  is_unlimited: boolean;
}

export async function getUsage() {
  return fetchApi<UsageStats>("/api/billing/usage");
}

export interface PlanInfo {
  name: string;
  limit_minutes: number | null;
  price: string;
  features: string[];
}

export async function getPlans() {
  return fetchApi<PlanInfo[]>("/api/billing/plans");
}
