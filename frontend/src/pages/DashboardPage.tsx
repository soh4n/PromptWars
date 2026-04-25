/** Dashboard page — stats, progress, recent sessions. */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { gamificationApi, sessionsApi, type GamificationProfile, type SessionItem } from "../services/api";
import { STRINGS } from "../constants/strings";
import { ROUTES } from "../constants/routes";
import { Flame, Zap, GraduationCap, BookOpen, ArrowRight, Loader2 } from "lucide-react";
import "./DashboardPage.css";

export function DashboardPage() {
  const { profile } = useAuth();
  const [stats, setStats] = useState<GamificationProfile | null>(null);
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, sess] = await Promise.all([gamificationApi.profile(), sessionsApi.list(5)]);
        setStats(s);
        setSessions(sess);
      } catch (err) {
        console.error("Dashboard load error:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="dash-loading" role="status" aria-label="Loading dashboard">
        <Loader2 size={40} style={{ animation: "spin 1s linear infinite", color: "var(--color-primary)" }} />
      </div>
    );
  }

  const displayName = profile?.display_name?.split(" ")[0] || "Learner";

  return (
    <div className="dashboard">
      <div className="animated-bg" aria-hidden="true" />

      <section className="dash-welcome" aria-label="Welcome section">
        <div>
          <h1>{STRINGS.WELCOME_BACK}, {displayName}!</h1>
          <p className="dash-welcome-sub">{STRINGS.APP_DESCRIPTION}</p>
        </div>
        <Link to={ROUTES.LEARN} className="btn btn-primary btn-lg">
          <GraduationCap size={20} aria-hidden="true" /> {STRINGS.START_LEARNING}
        </Link>
      </section>

      <section className="grid-stats" aria-label="Your stats">
        <div className="clay-card stat-card">
          <div className="stat-icon stat-icon-streak"><Flame size={24} aria-hidden="true" /></div>
          <div className="stat-value">{stats?.streak_days ?? 0}</div>
          <div className="stat-label">{STRINGS.DAILY_STREAK}</div>
        </div>
        <div className="clay-card stat-card">
          <div className="stat-icon stat-icon-xp"><Zap size={24} aria-hidden="true" /></div>
          <div className="stat-value">{stats?.total_xp?.toLocaleString() ?? 0}</div>
          <div className="stat-label">{STRINGS.TOTAL_XP}</div>
        </div>
        <div className="clay-card stat-card">
          <div className="stat-icon stat-icon-level"><GraduationCap size={24} aria-hidden="true" /></div>
          <div className="stat-value">{stats?.level ?? 1}</div>
          <div className="stat-label">{STRINGS.CURRENT_LEVEL}</div>
        </div>
        <div className="clay-card stat-card">
          <div className="stat-icon stat-icon-topics"><BookOpen size={24} aria-hidden="true" /></div>
          <div className="stat-value">{stats?.topics_explored ?? 0}</div>
          <div className="stat-label">{STRINGS.TOPICS_MASTERED}</div>
        </div>
      </section>

      {stats && (
        <section className="clay-card dash-progress-card" aria-label="Level progress">
          <h3>Level {stats.level} Progress</h3>
          <div className="progress-bar" role="progressbar" aria-valuenow={stats.level_progress_percent}
            aria-valuemin={0} aria-valuemax={100} aria-label="XP progress to next level">
            <div className="progress-bar-fill" style={{ width: `${stats.level_progress_percent}%` }} />
          </div>
          <p className="dash-progress-text">{stats.xp_to_next_level} XP to Level {stats.level + 1}</p>
        </section>
      )}

      {sessions.length > 0 && (
        <section aria-label="Recent sessions">
          <h2 className="dash-section-title">{STRINGS.RECENT_SESSIONS}</h2>
          <div className="dash-sessions-grid">
            {sessions.map(s => (
              <Link key={s.id} to={`${ROUTES.LEARN}?session=${s.id}`} className="clay-card dash-session-card">
                <div className="dash-session-topic">{s.topic}</div>
                <div className="dash-session-meta">
                  <span className="badge badge-primary">Level {s.difficulty_level}</span>
                  <span className="dash-session-msgs">{s.message_count} messages</span>
                </div>
                <div className="dash-session-continue">
                  {STRINGS.CONTINUE_LEARNING} <ArrowRight size={16} aria-hidden="true" />
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
