/** Achievements page — grid of badges with earned/locked states. */
import { useEffect, useState } from "react";
import { gamificationApi, type Achievement } from "../services/api";
import { STRINGS } from "../constants/strings";
import { Award, Lock, Star, Flame, BookOpen, Target, Zap, Trophy, Loader2 } from "lucide-react";
import "./AchievementsPage.css";

const ICON_MAP: Record<string, React.ReactNode> = {
  award: <Award size={28} />, star: <Star size={28} />, flame: <Flame size={28} />,
  book: <BookOpen size={28} />, target: <Target size={28} />, zap: <Zap size={28} />,
  trophy: <Trophy size={28} />,
};

export function AchievementsPage() {
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    gamificationApi.achievements().then(setAchievements).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="dash-loading" role="status"><Loader2 size={40} style={{ animation: "spin 1s linear infinite", color: "var(--color-primary)" }} /></div>;

  const earned = achievements.filter(a => a.is_earned);
  const locked = achievements.filter(a => !a.is_earned);

  return (
    <div className="achievements-page">
      <div className="animated-bg" aria-hidden="true" />
      <h1>{STRINGS.ACHIEVEMENTS_TITLE}</h1>
      <p className="achv-subtitle">{earned.length} of {achievements.length} earned</p>

      {earned.length > 0 && (
        <section aria-label="Earned achievements">
          <h2 className="achv-section-title">Earned</h2>
          <div className="achv-grid">
            {earned.map(a => (
              <div key={a.id} className="clay-card achv-card achv-earned">
                <div className="achv-icon">{ICON_MAP[a.icon] || <Award size={28} />}</div>
                <h3 className="achv-name">{a.name}</h3>
                <p className="achv-desc">{a.description}</p>
                <div className="badge badge-accent">+{a.xp_reward} XP</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {locked.length > 0 && (
        <section aria-label="Locked achievements">
          <h2 className="achv-section-title">Locked</h2>
          <div className="achv-grid">
            {locked.map(a => (
              <div key={a.id} className="clay-card achv-card achv-locked">
                <div className="achv-icon achv-icon-locked"><Lock size={28} /></div>
                <h3 className="achv-name">{a.name}</h3>
                <p className="achv-desc">{a.description}</p>
                <div className="badge badge-warning">+{a.xp_reward} XP</div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
