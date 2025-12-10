import type { ReactNode } from 'react';

import { useAuth } from '../contexts/auth-context';
import { LoadingSpinner } from '@/features/layout/components/loading-spinner';

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (!isAuthenticated) {
    window.location.href = '/accounts/login/?next=/app/';
    return null;
  }

  return <>{children}</>;
}
