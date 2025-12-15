import { type ReactNode, createContext, useContext, useEffect } from 'react';

import { useQuery } from '@tanstack/react-query';
import posthog from 'posthog-js';

import { usersMeRetrieveOptions } from '@/services/{{ project_slug }}/@tanstack/react-query.gen';
import type { User } from '@/services/{{ project_slug }}/types.gen';

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: Error | null;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const {
    data: user,
    isLoading,
    error,
  } = useQuery({
    ...usersMeRetrieveOptions(),
    retry: false,
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const isAuthenticated = !!user;

  // Identify user in PostHog when authenticated
  useEffect(() => {
    if (user) {
      posthog.identify(String(user.id), {
        email: user.email,
      });
    }
  }, [user]);

  const logout = () => {
    posthog.reset();
    window.location.href = '/accounts/logout/';
  };

  const value: AuthContextType = {
    user: user || null,
    isAuthenticated,
    isLoading,
    error: error as Error | null,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
