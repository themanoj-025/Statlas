"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MePayload, SubscriptionStatusPayload } from "@/lib/types";

type AuthState = {
  user: MePayload | null;
  status: "loading" | "signed-out" | "signed-in";
  subscription: SubscriptionStatusPayload | null;
  error: string | null;
  clearError: () => void;
  refresh: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<MePayload | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionStatusPayload | null>(null);
  const [status, setStatus] = useState<AuthState["status"]>("loading");

  const refresh = useCallback(async () => {
    try {
      const [me, sub] = await Promise.all([api.me(), api.subscription()]);
      setUser(me);
      setSubscription(sub);
      setStatus("signed-in");
    } catch {
      setUser(null);
      setSubscription(null);
      setStatus("signed-out");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const [error, setError] = useState<string | null>(null);
  const clearError = useCallback(() => setError(null), []);

  const login = useCallback(
    async (email: string, password: string) => {
      setError(null);
      const me = await api.login(email, password);
      setUser(me);
      setStatus("signed-in");
      await refresh();
    },
    [refresh]
  );

  const register = useCallback(
    async (email: string, password: string) => {
      setError(null);
      const me = await api.register(email, password);
      setUser(me);
      setStatus("signed-in");
      await refresh();
    },
    [refresh]
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
      setSubscription(null);
      setStatus("signed-out");
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, status, subscription, error, clearError, refresh, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
