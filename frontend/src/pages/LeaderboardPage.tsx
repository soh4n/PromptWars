/** Leaderboard page — top learners by XP. */
import { useEffect, useState } from "react";
import { gamificationApi, type LeaderboardData } from "../services/api";
import { STRINGS } from "../constants/strings";
import { Medal, Crown, Loader2 } from "lucide-react";
import "./LeaderboardPage.css";

export function LeaderboardPage() {
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    gamificationApi.leaderboard(50).then(setData).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="dash-loading" role="status"><Loader2 size={40} style={{ animation: "spin 1s linear infinite", color: "var(--color-primary)" }} /></div>;

  return (
    <div className="leaderboard-page">
      <div className="animated-bg" aria-hidden="true" />
      <h1><Medal size={28} aria-hidden="true" /> {STRINGS.LEADERBOARD_TITLE}</h1>
      {data?.current_user_rank && <p className="lb-your-rank">Your rank: <strong>#{data.current_user_rank}</strong></p>}

      <div className="clay-card lb-table-card">
        <table className="lb-table" role="table" aria-label="XP Leaderboard">
          <thead>
            <tr>
              <th scope="col">{STRINGS.RANK}</th>
              <th scope="col">Learner</th>
              <th scope="col">Level</th>
              <th scope="col">XP</th>
            </tr>
          </thead>
          <tbody>
            {data?.entries.map(entry => (
              <tr key={entry.user_id} className={entry.rank <= 3 ? "lb-top" : ""}>
                <td className="lb-rank">
                  {entry.rank === 1 ? <Crown size={18} className="lb-gold" aria-label="1st place" /> :
                   entry.rank === 2 ? <Medal size={18} className="lb-silver" aria-label="2nd place" /> :
                   entry.rank === 3 ? <Medal size={18} className="lb-bronze" aria-label="3rd place" /> :
                   `#${entry.rank}`}
                </td>
                <td className="lb-name">
                  <div className="lb-avatar" aria-hidden="true">
                    {entry.avatar_url ? <img src={entry.avatar_url} alt="" width={32} height={32} /> :
                     <span>{entry.display_name.charAt(0)}</span>}
                  </div>
                  {entry.display_name}
                </td>
                <td><span className="badge badge-primary">Lv. {entry.level}</span></td>
                <td className="lb-xp">{entry.total_xp.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
