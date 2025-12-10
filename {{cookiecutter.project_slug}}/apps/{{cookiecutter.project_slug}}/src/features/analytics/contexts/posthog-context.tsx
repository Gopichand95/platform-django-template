import { type ReactNode, useEffect } from 'react';

import posthog from 'posthog-js';

interface PostHogProviderProps {
  children: ReactNode;
}

export function PostHogProvider({ children }: PostHogProviderProps) {
  useEffect(() => {
    // Only initialize PostHog in production
    const posthogKey = import.meta.env.VITE_POSTHOG_KEY;
    const posthogHost = import.meta.env.VITE_POSTHOG_HOST || 'https://app.posthog.com';

    if (posthogKey && import.meta.env.PROD) {
      posthog.init(posthogKey, {
        api_host: posthogHost,
        capture_pageview: true,
        capture_pageleave: true,
      });
    }
  }, []);

  return <>{children}</>;
}
