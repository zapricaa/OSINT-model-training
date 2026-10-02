/**
 * ZAPRICA Global State Store (Zustand)
 *
 * Lightweight state management for auth, cases, and UI state.
 */

import { create } from "zustand";
import { api, User, Case, Investigation } from "./api";

// ── Auth Store ────────────────────────────────────────────────

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    org_name: string;
    org_slug: string;
    email: string;
    password: string;
    full_name: string;
  }) => Promise<void>;
  logout: () => void;
  loadFromStorage: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: true,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.login(email, password);
      localStorage.setItem("zaprica_token", response.access_token);
      set({ user: response.user, token: response.access_token, isLoading: false });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Login failed";
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.register(data);
      localStorage.setItem("zaprica_token", response.access_token);
      set({ user: response.user, token: response.access_token, isLoading: false });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Registration failed";
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  logout: () => {
    localStorage.removeItem("zaprica_token");
    set({ user: null, token: null, error: null });
  },

  loadFromStorage: async () => {
    const token = localStorage.getItem("zaprica_token");
    if (!token) {
      set({ isLoading: false });
      return;
    }
    try {
      const user = await api.getMe();
      set({ user, token, isLoading: false });
    } catch {
      localStorage.removeItem("zaprica_token");
      set({ user: null, token: null, isLoading: false });
    }
  },
}));

// ── App Store ─────────────────────────────────────────────────

interface AppState {
  cases: Case[];
  currentCase: Case | null;
  investigations: Investigation[];
  isLoadingCases: boolean;
  isLoadingInvestigations: boolean;

  loadCases: () => Promise<void>;
  setCurrentCase: (c: Case | null) => void;
  loadInvestigations: (caseId: string) => Promise<void>;
  addCase: (c: Case) => void;
  addInvestigation: (inv: Investigation) => void;
  updateInvestigation: (inv: Investigation) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  cases: [],
  currentCase: null,
  investigations: [],
  isLoadingCases: false,
  isLoadingInvestigations: false,

  loadCases: async () => {
    set({ isLoadingCases: true });
    try {
      const response = await api.listCases({ page_size: 50 });
      set({ cases: response.cases, isLoadingCases: false });
    } catch {
      set({ isLoadingCases: false });
    }
  },

  setCurrentCase: (c) => set({ currentCase: c }),

  loadInvestigations: async (caseId) => {
    set({ isLoadingInvestigations: true });
    try {
      const investigations = await api.listInvestigations(caseId);
      set({ investigations, isLoadingInvestigations: false });
    } catch {
      set({ isLoadingInvestigations: false });
    }
  },

  addCase: (c) => set((s) => ({ cases: [c, ...s.cases] })),

  addInvestigation: (inv) =>
    set((s) => ({ investigations: [inv, ...s.investigations] })),

  updateInvestigation: (inv) =>
    set((s) => ({
      investigations: s.investigations.map((i) =>
        i.id === inv.id ? inv : i
      ),
    })),
}));
