/** Typed API client with auth token injection. */

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://localhost:8000" : "");

async function getAuthToken(): Promise<string | null> {
  const { auth } = await import("./firebase");
  const user = auth.currentUser;
  if (!user) return null;
  return user.getIdToken();
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// ── Auth ────────────────────────────────────────────────────────
export const authApi = {
  login: (idToken: string) =>
    apiFetch<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ id_token: idToken }) }),
  register: (email: string, password: string, displayName: string) =>
    apiFetch<AuthResponse>("/auth/register", {
      method: "POST", body: JSON.stringify({ email, password, display_name: displayName }),
    }),
  resetPassword: (email: string) =>
    apiFetch<{ message: string }>("/auth/reset-password", { method: "POST", body: JSON.stringify({ email }) }),
  getMe: () => apiFetch<UserProfile>("/auth/me"),
};

// ── Assistant ───────────────────────────────────────────────────
export const assistantApi = {
  chat: (message: string, sessionId?: string, topic?: string) =>
    apiFetch<ChatResponse>("/assistant/chat", {
      method: "POST", body: JSON.stringify({ message, session_id: sessionId, topic }),
    }),
  quiz: (topic: string, numQuestions?: number, sessionId?: string) =>
    apiFetch<QuizResponse>("/assistant/quiz", {
      method: "POST", body: JSON.stringify({ topic, num_questions: numQuestions || 3, session_id: sessionId }),
    }),
  evaluate: (sessionId: string, question: string, userAnswer: string, correctAnswer: string, topic: string) =>
    apiFetch<EvaluateResponse>("/assistant/evaluate", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, question, user_answer: userAnswer, correct_answer: correctAnswer, topic }),
    }),
};

// ── Sessions ────────────────────────────────────────────────────
export const sessionsApi = {
  list: (limit = 20) => apiFetch<SessionItem[]>(`/sessions?limit=${limit}`),
  end: (sessionId: string) => apiFetch<void>(`/sessions/${sessionId}`, { method: "DELETE" }),
};

// ── Gamification ────────────────────────────────────────────────
export const gamificationApi = {
  profile: () => apiFetch<GamificationProfile>("/gamification/profile"),
  achievements: () => apiFetch<Achievement[]>("/gamification/achievements"),
  leaderboard: (limit = 50) => apiFetch<LeaderboardData>(`/gamification/leaderboard?limit=${limit}`),
  mastery: () => apiFetch<MasteryItem[]>("/gamification/mastery"),
};

// ── Types ───────────────────────────────────────────────────────
export interface AuthResponse { user: UserProfile; message: string }
export interface UserProfile {
  id: string; email: string; display_name: string; avatar_url: string | null;
  total_xp: number; level: number; streak_days: number; created_at: string;
}
export interface ChatResponse {
  message: string; session_id: string; intent: string; xp_earned: number;
  achievements_earned: string[]; difficulty_level: number; model_used: string;
}
export interface QuizQuestion { question: string; options: string[]; correct_index: number; explanation: string }
export interface QuizResponse { questions: QuizQuestion[]; topic: string; difficulty_level: number; session_id: string }
export interface EvaluateResponse {
  is_correct: boolean; feedback: string; xp_earned: number;
  new_mastery_score: number; achievements_earned: string[];
}
export interface SessionItem {
  id: string; topic: string; difficulty_level: number; status: string;
  started_at: string; ended_at: string | null; message_count: number;
}
export interface GamificationProfile {
  total_xp: number; level: number; streak_days: number; longest_streak: number;
  sessions_completed: number; quiz_correct_total: number; topics_explored: number;
  xp_to_next_level: number; level_progress_percent: number;
}
export interface Achievement {
  id: string; name: string; description: string; icon: string;
  xp_reward: number; is_earned: boolean; earned_at: string | null;
}
export interface LeaderboardEntry {
  rank: number; user_id: string; display_name: string;
  avatar_url: string | null; total_xp: number; level: number;
}
export interface LeaderboardData { entries: LeaderboardEntry[]; current_user_rank: number | null }
export interface MasteryItem { topic: string; mastery_score: number; questions_answered: number; correct_answers: number }
