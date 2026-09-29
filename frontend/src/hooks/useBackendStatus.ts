import { useState, useEffect, useCallback } from 'react';
import { checkBackendHealth, type HealthResponse } from '../services/api';

export type BackendStatus = 'checking' | 'online' | 'offline';

export interface UseBackendStatusReturn {
  status: BackendStatus;
  message: string;
  activeSessions: number;
  version: string | null;
  checkStatus: () => Promise<boolean>;
  retryConnection: () => Promise<boolean>;
  isChecking: boolean;
  isOnline: boolean;
  isOffline: boolean;
  // Aliases for seamless backward compatibility
  isReady: boolean;
  isWaking: boolean;
  isFailed: boolean;
}

// Module-level singleton state across all hook consumers
let sharedStatus: BackendStatus = 'checking';
let sharedMessage: string = 'Checking backend...';
let sharedActiveSessions: number = 0;
let sharedVersion: string | null = null;
let hasCheckedOnce = false;
let activeCheckPromise: Promise<boolean> | null = null;
const listeners = new Set<() => void>();

function notifyListeners() {
  listeners.forEach((listener) => {
    try {
      listener();
    } catch {
      // Ignore subscriber errors
    }
  });
}

async function runHealthCheck(): Promise<boolean> {
  if (activeCheckPromise) {
    return activeCheckPromise;
  }

  activeCheckPromise = (async () => {
    let lastError: any = null;

    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        const res: HealthResponse = await checkBackendHealth(15000);
        if (res && (res.status === 'ok' || !res.status)) {
          sharedStatus = 'online';
          sharedMessage = 'Backend Online';
          sharedActiveSessions = res.active_sessions || 0;
          sharedVersion = res.version || null;
          notifyListeners();
          return true;
        } else {
          lastError = new Error(`Unexpected health payload: ${JSON.stringify(res)}`);
        }
      } catch (err: any) {
        lastError = err;
      }

      // If the first attempt failed, wait 3 seconds and retry ONCE automatically
      if (attempt === 1) {
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    }

    // Diagnostic console.error (dev-visible only, not shown to users)
    const failureMode = lastError?.isTimeout
      ? 'Timeout (exceeded 15s)'
      : lastError?.status
      ? `Non-200 response (HTTP ${lastError.status})`
      : `Network error (${lastError?.message || 'Failed to fetch'})`;

    console.error(`[CleanIQ Diagnostic] Health check failed after retry. Failure mode: ${failureMode}`, lastError);

    sharedStatus = 'offline';
    sharedMessage = "Backend Unavailable — CleanIQ's processing server is temporarily unavailable";
    notifyListeners();
    return false;
  })().finally(() => {
    hasCheckedOnce = true;
    activeCheckPromise = null;
  });

  return activeCheckPromise;
}

export function triggerHealthCheck(): Promise<boolean> {
  activeCheckPromise = null;
  sharedStatus = 'checking';
  sharedMessage = 'Checking backend...';
  notifyListeners();
  return runHealthCheck();
}

export function useBackendStatus(): UseBackendStatusReturn {
  const [status, setStatus] = useState<BackendStatus>(sharedStatus);
  const [activeSessions, setActiveSessions] = useState<number>(sharedActiveSessions);
  const [version, setVersion] = useState<string | null>(sharedVersion);
  const [message, setMessage] = useState<string>(sharedMessage);

  useEffect(() => {
    // On app mount, perform the single health check if not yet checked
    if (!hasCheckedOnce && !activeCheckPromise) {
      triggerHealthCheck();
    }

    const handleUpdate = () => {
      setStatus(sharedStatus);
      setActiveSessions(sharedActiveSessions);
      setVersion(sharedVersion);
      setMessage(sharedMessage);
    };

    listeners.add(handleUpdate);

    return () => {
      listeners.delete(handleUpdate);
    };
  }, []);

  const checkStatus = useCallback(async () => {
    return await triggerHealthCheck();
  }, []);

  const isOnline = status === 'online';
  const isOffline = status === 'offline';
  const isChecking = status === 'checking';

  return {
    status,
    message,
    activeSessions,
    version,
    checkStatus,
    retryConnection: checkStatus,
    isChecking,
    isOnline,
    isOffline,
    isReady: isOnline,
    isWaking: false,
    isFailed: isOffline,
  };
}
