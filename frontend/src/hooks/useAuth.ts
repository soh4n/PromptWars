/** Auth hook — Firebase auth state + all auth methods. */
import { useState, useEffect, useCallback } from "react";
import {
  auth,
  googleProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendPasswordResetEmail,
  updateProfile,
  firebaseSignOut,
  onAuthStateChanged,
  type User,
} from "../services/firebase";
import { authApi, type UserProfile } from "../services/api";
import { useAuthStore } from "../store/authStore";

export function useAuth() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { user, setUser, clearUser, setProfile, profile } = useAuthStore();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser: User | null) => {
      if (firebaseUser) {
        setUser(firebaseUser);
        try {
          const token = await firebaseUser.getIdToken();
          const res = await authApi.login(token);
          setProfile(res.user);
        } catch {
          // First login — profile will be created
        }
      } else {
        clearUser();
      }
    });
    return unsubscribe;
  }, [setUser, clearUser, setProfile]);

  const signInWithEmail = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const cred = await signInWithEmailAndPassword(auth, email, password);
      const token = await cred.user.getIdToken();
      const res = await authApi.login(token);
      setProfile(res.user);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Login failed";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setProfile]);

  const signUpWithEmail = useCallback(async (email: string, password: string, displayName: string) => {
    setLoading(true);
    setError(null);
    try {
      const cred = await createUserWithEmailAndPassword(auth, email, password);
      await updateProfile(cred.user, { displayName });
      const token = await cred.user.getIdToken();
      await authApi.login(token);
      const me = await authApi.getMe();
      setProfile(me);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Registration failed";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setProfile]);

  const signInWithGoogle = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const cred = await signInWithPopup(auth, googleProvider);
      const token = await cred.user.getIdToken();
      const res = await authApi.login(token);
      setProfile(res.user);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Google sign-in failed";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setProfile]);

  const resetPassword = useCallback(async (email: string) => {
    setLoading(true);
    setError(null);
    try {
      await sendPasswordResetEmail(auth, email);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Reset failed";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    await firebaseSignOut(auth);
    clearUser();
  }, [clearUser]);

  return {
    user, profile, loading, error,
    isAuthenticated: !!user,
    signInWithEmail, signUpWithEmail, signInWithGoogle,
    resetPassword, signOut,
  };
}
