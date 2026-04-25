/** Forgot password page — sends Firebase reset email. */
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { STRINGS } from "../constants/strings";
import { ROUTES } from "../constants/routes";
import { BookOpen, Mail, ArrowLeft, CheckCircle } from "lucide-react";
import "./AuthPages.css";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const { resetPassword, loading, error } = useAuth();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await resetPassword(email);
      setSent(true);
    } catch { /* error set in hook */ }
  }

  return (
    <div className="auth-page">
      <div className="animated-bg" aria-hidden="true" />
      <main className="auth-container" id="main-content">
        <div className="clay-card auth-card">
          <div className="auth-logo" aria-hidden="true"><BookOpen size={36} /></div>
          <h1 className="auth-title">{STRINGS.FORGOT_PASSWORD_TITLE}</h1>
          <p className="auth-subtitle">{STRINGS.FORGOT_PASSWORD_SUBTITLE}</p>

          {error && <div role="alert" aria-live="assertive" className="auth-error">{error}</div>}

          {sent ? (
            <div className="auth-success" role="status">
              <CheckCircle size={48} style={{ color: "var(--color-accent)", margin: "0 auto 1rem" }} />
              <p>{STRINGS.RESET_LINK_SENT}</p>
              <Link to={ROUTES.LOGIN} className="btn btn-indigo btn-full" style={{ marginTop: "1.5rem" }}>
                Back to Login
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              <div className="form-group">
                <label htmlFor="reset-email" className="form-label">Email</label>
                <div className="input-icon-wrapper">
                  <Mail size={18} className="input-icon" aria-hidden="true" />
                  <input id="reset-email" type="email" className="form-input input-with-icon"
                    placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)}
                    required aria-required="true" autoComplete="email" />
                </div>
              </div>
              <button type="submit" className="btn btn-indigo btn-full btn-lg"
                disabled={loading} aria-busy={loading}>
                {loading ? STRINGS.SENDING : "Send Reset Link"}
              </button>
              <Link to={ROUTES.LOGIN} className="auth-back-link">
                <ArrowLeft size={16} /> Back to Login
              </Link>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
