/** Client-side auth state store. */
import { create } from "zustand";
import type { User } from "../services/firebase";
import type { UserProfile } from "../services/api";

interface AuthState {
  user: User | null;
  profile: UserProfile | null;
  isLoading: boolean;
  setUser: (user: User) => void;
  setProfile: (profile: UserProfile) => void;
  clearUser: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  profile: null,
  isLoading: true,
  setUser: (user) => set({ user, isLoading: false }),
  setProfile: (profile) => set({ profile }),
  clearUser: () => set({ user: null, profile: null, isLoading: false }),
}));
