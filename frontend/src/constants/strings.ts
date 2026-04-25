/** All user-visible strings — internationalisation-ready. */

export const STRINGS = {
  APP_NAME: "LearnAI",
  APP_TAGLINE: "Your Intelligent Learning Companion",
  APP_DESCRIPTION: "Master any topic with AI-powered adaptive learning and gamification",

  // Auth
  LOGIN_TITLE: "Welcome Back",
  LOGIN_SUBTITLE: "Sign in to continue your learning journey",
  REGISTER_TITLE: "Create Account",
  REGISTER_SUBTITLE: "Start your personalized learning journey today",
  FORGOT_PASSWORD_TITLE: "Reset Password",
  FORGOT_PASSWORD_SUBTITLE: "Enter your email and we'll send you a reset link",
  SIGN_IN_GOOGLE: "Continue with Google",
  SIGN_IN_EMAIL: "Sign in",
  SIGN_UP: "Create Account",
  FORGOT_PASSWORD: "Forgot password?",
  ALREADY_HAVE_ACCOUNT: "Already have an account?",
  DONT_HAVE_ACCOUNT: "Don't have an account?",
  RESET_LINK_SENT: "If an account exists with this email, a reset link has been sent.",
  SIGN_OUT: "Sign Out",

  // Navigation
  NAV_DASHBOARD: "Dashboard",
  NAV_LEARN: "Learn",
  NAV_ACHIEVEMENTS: "Achievements",
  NAV_LEADERBOARD: "Leaderboard",

  // Dashboard
  WELCOME_BACK: "Welcome back",
  DAILY_STREAK: "Day Streak",
  TOTAL_XP: "Total XP",
  CURRENT_LEVEL: "Level",
  TOPICS_MASTERED: "Topics",
  RECENT_SESSIONS: "Recent Sessions",
  CONTINUE_LEARNING: "Continue",
  START_LEARNING: "Start Learning",

  // Learning
  CHAT_PLACEHOLDER: "Ask me anything or type a topic to learn...",
  QUIZ_ME: "Quiz Me",
  EXPLAIN_SIMPLER: "Explain Simpler",
  GIVE_EXAMPLE: "Give Example",
  SUMMARIZE: "Summarize",
  SENDING: "Thinking...",

  // Gamification
  ACHIEVEMENTS_TITLE: "Achievements",
  LEADERBOARD_TITLE: "Leaderboard",
  LEVEL_UP: "Level Up!",
  XP_EARNED: "XP earned",
  RANK: "Rank",

  // Errors
  ERROR_GENERIC: "Something went wrong. Please try again.",
  ERROR_AUTH_FAILED: "Authentication failed. Please try again.",
  ERROR_NETWORK: "Network error. Please check your connection.",
} as const;
