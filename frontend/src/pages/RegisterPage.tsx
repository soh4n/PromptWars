/** Register page — email/password + Google sign-up. */
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { STRINGS } from "../constants/strings";
import { ROUTES } from "../constants/routes";
import { BookOpen, Mail, Lock, User, Eye, EyeOff } from "lucide-react";
import "./AuthPages.css";

export function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showPw, setShowPw] = useState(false);
  const { signUpWithEmail, signInWithGoogle, loading, error } = useAuth();
  const navigate = useNavigate();

  const passwordsMatch = password === confirmPw;
  const passwordStrong = password.length >= 8;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!passwordsMatch || !passwordStrong) return;
    try {
      await signUpWithEmail(email, password, name);
      navigate(ROUTES.DASHBOARD);
    } catch { /* error set in hook */ }
  }

  async function handleGoogle() {
    try {
      await signInWithGoogle();
      navigate(ROUTES.DASHBOARD);
    } catch { /* error set in hook */ }
  }

  return (
    <div className="auth-page">
      <div className="animated-bg" aria-hidden="true" />
      <main className="auth-container" id="main-content">
        <div className="clay-card auth-card">
          <div className="auth-logo" aria-hidden="true"><BookOpen size={36} /></div>
          <h1 className="auth-title">{STRINGS.REGISTER_TITLE}</h1>
          <p className="auth-subtitle">{STRINGS.REGISTER_SUBTITLE}</p>

          {error && <div role="alert" aria-live="assertive" className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit} noValidate>
            <div className="form-group">
              <label htmlFor="reg-name" className="form-label">Display Name</label>
              <div className="input-icon-wrapper">
                <User size={18} className="input-icon" aria-hidden="true" />
                <input id="reg-name" type="text" className="form-input input-with-icon"
                  placeholder="Your name" value={name} onChange={e => setName(e.target.value)}
                  required aria-required="true" autoComplete="name" />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="reg-email" className="form-label">Email</label>
              <div className="input-icon-wrapper">
                <Mail size={18} className="input-icon" aria-hidden="true" />
                <input id="reg-email" type="email" className="form-input input-with-icon"
                  placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)}
                  required aria-required="true" autoComplete="email" />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="reg-password" className="form-label">Password</label>
              <div className="input-icon-wrapper">
                <Lock size={18} className="input-icon" aria-hidden="true" />
                <input id="reg-password" type={showPw ? "text" : "password"} className="form-input input-with-icon"
                  placeholder="Min 8 characters" value={password} onChange={e => setPassword(e.target.value)}
                  required aria-required="true" minLength={8}
                  aria-describedby="pw-strength" autoComplete="new-password" />
                <button type="button" className="input-toggle" onClick={() => setShowPw(!showPw)}
                  aria-label={showPw ? "Hide password" : "Show password"}>
                  {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {password.length > 0 && (
                <div id="pw-strength" className={`pw-strength ${passwordStrong ? "strong" : "weak"}`}>
                  {passwordStrong ? "Strong password" : "Password must be at least 8 characters"}
                </div>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="reg-confirm" className="form-label">Confirm Password</label>
              <div className="input-icon-wrapper">
                <Lock size={18} className="input-icon" aria-hidden="true" />
                <input id="reg-confirm" type="password" className="form-input input-with-icon"
                  placeholder="Confirm password" value={confirmPw} onChange={e => setConfirmPw(e.target.value)}
                  required aria-required="true" aria-describedby="pw-match" autoComplete="new-password" />
              </div>
              {confirmPw.length > 0 && !passwordsMatch && (
                <div id="pw-match" className="form-error">Passwords do not match</div>
              )}
            </div>

            <button type="submit" className="btn btn-indigo btn-full btn-lg"
              disabled={loading || !passwordsMatch || !passwordStrong} aria-busy={loading}>
              {loading ? STRINGS.SENDING : STRINGS.SIGN_UP}
            </button>
          </form>

          <div className="auth-divider"><span>or</span></div>

          <button type="button" className="btn btn-google btn-full" onClick={handleGoogle}
            disabled={loading} aria-label={STRINGS.SIGN_IN_GOOGLE}>
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
              <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"/>
              <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z"/>
              <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.997 8.997 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/>
              <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"/>
            </svg>
            {STRINGS.SIGN_IN_GOOGLE}
          </button>

          <p className="auth-switch">
            {STRINGS.ALREADY_HAVE_ACCOUNT} <Link to={ROUTES.LOGIN}>{STRINGS.SIGN_IN_EMAIL}</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
