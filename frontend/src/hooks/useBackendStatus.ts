import { useState, useEffect, useCallback } from 'react';
import { checkBackendHealth, type HealthResponse } from '../services/api';

export type BackendStatus = 'checking' | 'waking' | 'online' | 'offline';

export interface UseBackendStatusReturn {
  status: BackendStatus;
  message: string;
  activeSessions: number;
  version: string | null;
  checkStatus: () => Promise<boolean>;
  retryConnection: () => Promise<boolean>;
  isChecking: boolean;
  isWaking: boolean;
  isOnline: boolean;
  isOffline: boolean;
  // Aliases for seamless backward compatibility
  isReady: boolean;
  isFailed: boolean;
}

// ─── Module-level singleton state shared across all hook consumers ───────────

let sharedStatus: BackendStatus = 'checking';
let sharedMessage: string = 'Checking backend...';
let sharedActiveSessions: number = 0;
let sharedVersion: string | null = null;
let hasCheckedOnce = false;
let activeCheckPromise: Promise<boolean> | null = null;

// Timers and abort controllers that must be cleaned up
let retryTimerId: ReturnType<typeof setTimeout> | null = null;
let activeAbortController: AbortController | null = null;

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

function setSharedState(status: BackendStatus, message: string, sessions?: number, version?: string | null) {
  sharedStatus = status;
  sharedMessage = message;
  if (sessions !== undefined) sharedActiveSessions = sessions;
  if (version !== undefined) sharedVersion = version;
  notifyListeners();
}

function cancelPendingWork() {
  // Cancel any pending retry timer
  if (retryTimerId !== null) {
    clearTimeout(retryTimerId);
    retryTimerId = null;
  }
  // Abort any in-flight fetch
  if (activeAbortController) {
    activeAbortController.abort();
    activeAbortController = null;
  }
}

// ─── Single health check attempt (non-retrying) ─────────────────────────────

async function singleHealthCheck(timeoutMs: number): Promise<HealthResponse> {
  // Create a fresh AbortController for this attempt
  activeAbortController = new AbortController();
  return checkBackendHealth(timeoutMs, activeAbortController.signal);
}

// ─── Retry schedule: initial 60s, then 5s delay + 15s, then 10s delay + 15s ─

const RETRY_SCHEDULE = [
  { initialTimeoutMs: 60_000, label: 'Checking backend...',                        phase: 'checking' as const },
  { delayMs: 5_000, timeoutMs: 15_000, label: 'Waking up CleanIQ server...',       phase: 'waking' as const },
  { delayMs: 10_000, timeoutMs: 15_000, label: 'Waking up CleanIQ server...',      phase: 'waking' as const },
];

// ─── Full health check sequence with bounded retries ─────────────────────────

async function runHealthCheckSequence(): Promise<boolean> {
  if (activeCheckPromise) {
    return activeCheckPromise;
  }

  activeCheckPromise = (async () => {
    cancelPendingWork();

    for (let i = 0; i < RETRY_SCHEDULE.length; i++) {
      const step = RETRY_SCHEDULE[i];

      // Set the UI state for this phase
      if (i === 0) {
        setSharedState(step.phase, step.label);
      } else {
        // Wait before retrying
        setSharedState(step.phase, step.label);
        const delay = 'delayMs' in step ? step.delayMs! : 0;
        if (delay > 0) {
          await new Promise<void>((resolve) => {
            retryTimerId = setTimeout(() => {
              retryTimerId = null;
              resolve();
            }, delay);
          });
        }
      }

      const timeout = 'initialTimeoutMs' in step ? step.initialTimeoutMs! : ('timeoutMs' in step ? step.timeoutMs! : 15_000);

      try {
        const res = await singleHealthCheck(timeout);
        if (res && res.status === 'ok') {
          setSharedState('online', 'Backend Online', res.active_sessions || 0, res.version || null);
          return true;
        }
        // Unexpected payload — continue to next retry
        console.warn(`[CleanIQ] Health check returned unexpected payload:`, res);
      } catch (err: any) {
        const failureMode = err?.isTimeout
          ? `Timeout (${Math.round(timeout / 1000)}s)`
          : err?.status
          ? `HTTP ${err.status}`
          : `Network error (${err?.message || 'Failed to fetch'})`;

        console.warn(`[CleanIQ] Health check attempt ${i + 1}/${RETRY_SCHEDULE.length} failed: ${failureMode}`);

        // If this wasn't the last attempt, the loop continues
        // If it was the last attempt, we fall through to the offline state below
      }
    }

    // All retries exhausted
    setSharedState(
      'offline',
      "Backend Unavailable — CleanIQ's processing server didn't respond after multiple attempts",
    );
    return false;
  })().finally(() => {
    hasCheckedOnce = true;
    activeCheckPromise = null;
    activeAbortController = null;
  });

  return activeCheckPromise;
}

// ─── Public trigger (used for initial check and Retry Connection button) ─────

export function triggerHealthCheck(): Promise<boolean> {
  // Cancel any existing sequence before starting a new one
  cancelPendingWork();
  activeCheckPromise = null;
  setSharedState('checking', 'Checking backend...');
  return runHealthCheckSequence();
}

// ─── React Hook ──────────────────────────────────────────────────────────────

export function useBackendStatus(): UseBackendStatusReturn {
  const [status, setStatus] = useState<BackendStatus>(sharedStatus);
  const [activeSessions, setActiveSessions] = useState<number>(sharedActiveSessions);
  const [version, setVersion] = useState<string | null>(sharedVersion);
  const [message, setMessage] = useState<string>(sharedMessage);

  useEffect(() => {
    // On app mount, perform the health check sequence if not yet checked
    if (!hasCheckedOnce && !activeCheckPromise) {
      triggerHealthCheck();
    }

    const handleUpdate = () => {
      setStatus(sharedStatus);
      setActiveSessions(sharedActiveSessions);
      setVersion(sharedVersion);
      setMessage(sharedMessage);
    };

    // Sync immediately in case state changed between render and effect
    handleUpdate();

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
  const isWaking = status === 'waking';

  return {
    status,
    message,
    activeSessions,
    version,
    checkStatus,
    retryConnection: checkStatus,
    isChecking,
    isWaking,
    isOnline,
    isOffline,
    isReady: isOnline,
    isFailed: isOffline,
  };
}
