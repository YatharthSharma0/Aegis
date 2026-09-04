import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { get, post } from "../api/client";
import type { MeResponse, TokenResponse } from "../api/types";
import { useAuthStore } from "../state/authStore";

export function useAuth() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { accessToken, role, email, setSession, setEmail, clear } = useAuthStore();

  const login = async (userEmail: string, password: string) => {
    const tokens = await post<TokenResponse>("/api/v1/auth/login", {
      email: userEmail,
      password,
    });
    setSession({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      role: tokens.role as MeResponse["role"],
      email: userEmail,
    });
    const me = await get<MeResponse>("/api/v1/auth/me").catch(() => null);
    if (me) setEmail(me.email);
  };

  const logout = () => {
    clear();
    queryClient.clear();
    navigate("/login", { replace: true });
  };

  return {
    isAuthenticated: accessToken !== null,
    role,
    email,
    login,
    logout,
  };
}
