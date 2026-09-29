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
    try {
      const res: HealthResponse = await checkBackendHealth(5000);
      if (res && res.status === 'ok') {
        sharedStatus = 'online';
        sharedMessage = 'Backend Online';
        sharedActiveSessions = res.active_sessions || 0;
        sharedVersion = res.version || null;
        notifyListeners();
        return true;
      } else {
        sharedStatus = 'offline';
        sharedMessage = "Backend Unavailable — CleanIQ's processing server is temporarily unavailable";
        notifyListeners();
        return false;
      }
    } catch {
      sharedStatus = 'offline';
      sharedMessage = "Backend Unavailable — CleanIQ's processing server is temporarily unavailable";
      notifyListeners();
      return false;
    } finally {
      hasCheckedOnce = true;
      activeCheckPromise = null;
    }
  })();

  return activeCheckPromise;
}

export function triggerHealthCheck(): Promise<boolean> {
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
