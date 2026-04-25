/** Layout — navbar + main content area with skip-to-content link. */
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { STRINGS } from "../constants/strings";
import { ROUTES } from "../constants/routes";
import { BookOpen, LayoutDashboard, GraduationCap, Trophy, Medal, LogOut, User } from "lucide-react";
import "./Layout.css";

export function Layout() {
  const { profile, signOut } = useAuth();
  const navigate = useNavigate();

  async function handleSignOut() {
    await signOut();
    navigate(ROUTES.LOGIN);
  }

  return (
    <>
      <a href="#main-content" className="skip-link">Skip to main content</a>

      <header className="navbar clay-card" role="banner">
        <div className="navbar-inner">
          <NavLink to={ROUTES.DASHBOARD} className="navbar-brand" aria-label={`${STRINGS.APP_NAME} home`}>
            <div className="navbar-logo-icon" aria-hidden="true"><BookOpen size={22} /></div>
            <span className="navbar-logo-text">{STRINGS.APP_NAME}</span>
          </NavLink>

          <nav className="navbar-nav" role="navigation" aria-label="Main navigation">
            <NavLink to={ROUTES.DASHBOARD} className="nav-link" aria-label={STRINGS.NAV_DASHBOARD}>
              <LayoutDashboard size={20} aria-hidden="true" /><span>{STRINGS.NAV_DASHBOARD}</span>
            </NavLink>
            <NavLink to={ROUTES.LEARN} className="nav-link" aria-label={STRINGS.NAV_LEARN}>
              <GraduationCap size={20} aria-hidden="true" /><span>{STRINGS.NAV_LEARN}</span>
            </NavLink>
            <NavLink to={ROUTES.ACHIEVEMENTS} className="nav-link" aria-label={STRINGS.NAV_ACHIEVEMENTS}>
              <Trophy size={20} aria-hidden="true" /><span>{STRINGS.NAV_ACHIEVEMENTS}</span>
            </NavLink>
            <NavLink to={ROUTES.LEADERBOARD} className="nav-link" aria-label={STRINGS.NAV_LEADERBOARD}>
              <Medal size={20} aria-hidden="true" /><span>{STRINGS.NAV_LEADERBOARD}</span>
            </NavLink>
          </nav>

          <div className="navbar-user">
            {profile && (
              <div className="navbar-xp-badge badge badge-primary" aria-label={`Level ${profile.level}`}>
                Lv. {profile.level}
              </div>
            )}
            <div className="navbar-avatar" aria-hidden="true">
              {profile?.avatar_url ? (
                <img src={profile.avatar_url} alt="" width={36} height={36} />
              ) : (
                <User size={20} />
              )}
            </div>
            <button className="btn btn-ghost btn-sm" onClick={handleSignOut} aria-label={STRINGS.SIGN_OUT}>
              <LogOut size={18} aria-hidden="true" />
              <span className="nav-label-desktop">{STRINGS.SIGN_OUT}</span>
            </button>
          </div>
        </div>
      </header>

      <main id="main-content" className="page-content container">
        <Outlet />
      </main>
    </>
  );
}
