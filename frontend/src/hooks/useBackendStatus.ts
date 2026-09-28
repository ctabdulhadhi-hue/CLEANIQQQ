import { useState, useEffect, useCallback } from 'react';
import { checkBackendHealth, type HealthResponse } from '../services/api';

export type BackendStatus = 'checking' | 'waking' | 'ready' | 'failed';

interface UseBackendStatusReturn {
  status: BackendStatus;
  message: string;
  activeSessions: number;
  version: string | null;
  checkStatus: () => void;
  isReady: boolean;
  isWaking: boolean;
  isFailed: boolean;
}

const MAX_WAKE_TIME_MS = 90_000; // 90 seconds max wait for cold start
const POLL_INTERVAL_MS = 3_000;  // Poll every 3 seconds while waking
const WARM_POLL_INTERVAL_MS = 15_000; // Poll every 15s once connected

// Module-level singleton state across all hook consumers
let sharedStatus: BackendStatus = 'checking';
let sharedMessage: string = 'Checking backend status...';
let sharedActiveSessions: number = 0;
let sharedVersion: string | null = null;
let lastHealthyTime: number = 0;
let checkStartTime: number = Date.now();
let isCheckInProgress = false;
let globalTimer: ReturnType<typeof setInterval> | null = null;
let subscriberCount = 0;
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
  if (isCheckInProgress) return sharedStatus === 'ready';
  isCheckInProgress = true;

  try {
    const res: HealthResponse = await checkBackendHealth(4000);
    if (res && (res.status === 'ok' || res.status === 'healthy' || (res as any).ok)) {
      sharedStatus = 'ready';
      sharedMessage = 'Backend Online';
      sharedActiveSessions = res.active_sessions || 0;
      sharedVersion = res.version || null;
      lastHealthyTime = Date.now();
      notifyListeners();
      return true;
    } else {
      const elapsed = Date.now() - checkStartTime;
      if (elapsed >= MAX_WAKE_TIME_MS) {
        sharedStatus = 'failed';
        sharedMessage = "Backend didn't respond";
      } else {
        sharedStatus = 'waking';
        sharedMessage = 'Backend is starting (free-tier cold start, usually 20-45 seconds)';
      }
      notifyListeners();
    }
  } catch {
    const elapsed = Date.now() - checkStartTime;
    if (elapsed >= MAX_WAKE_TIME_MS) {
      sharedStatus = 'failed';
      sharedMessage = "Backend didn't respond";
    } else {
      sharedStatus = 'waking';
      sharedMessage = 'Backend is starting (free-tier cold start, usually 20-45 seconds)';
    }
    notifyListeners();
  } finally {
    isCheckInProgress = false;
  }
  return false;
}

function startPollingLoop() {
  if (globalTimer) {
    clearInterval(globalTimer);
  }

  const interval = sharedStatus === 'ready' ? WARM_POLL_INTERVAL_MS : POLL_INTERVAL_MS;
  globalTimer = setInterval(async () => {
    const wasReady = sharedStatus === 'ready';
    const isNowReady = await runHealthCheck();
    if (!wasReady && isNowReady) {
      // Transitioned to healthy: restart timer with slower warm polling interval
      startPollingLoop();
    }
  }, interval);
}

function triggerCheck() {
  checkStartTime = Date.now();
  if (sharedStatus !== 'ready') {
    sharedStatus = 'checking';
    sharedMessage = 'Connecting to backend...';
    notifyListeners();
  }
  runHealthCheck().then(() => {
    startPollingLoop();
  });
}

export function useBackendStatus(): UseBackendStatusReturn {
  // If confirmed healthy within the last 60 seconds, initialize as ready immediately
  const isRecentlyHealthy = sharedStatus === 'ready' && (Date.now() - lastHealthyTime < 60_000);

  const [status, setStatus] = useState<BackendStatus>(isRecentlyHealthy ? 'ready' : sharedStatus);
  const [activeSessions, setActiveSessions] = useState<number>(sharedActiveSessions);
  const [version, setVersion] = useState<string | null>(sharedVersion);
  const [message, setMessage] = useState<string>(isRecentlyHealthy ? 'Backend Online' : sharedMessage);

  useEffect(() => {
    subscriberCount++;
    if (subscriberCount === 1) {
      // First component mounted - trigger initial health check and polling
      triggerCheck();
    } else if (isRecentlyHealthy) {
      // Ensure local state is in sync with recently healthy singleton state
      setStatus('ready');
      setMessage('Backend Online');
      setActiveSessions(sharedActiveSessions);
      setVersion(sharedVersion);
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
      subscriberCount--;
      if (subscriberCount <= 0) {
        subscriberCount = 0;
        if (globalTimer) {
          clearInterval(globalTimer);
          globalTimer = null;
        }
      }
    };
  }, [isRecentlyHealthy]);

  const checkStatus = useCallback(() => {
    triggerCheck();
  }, []);

  return {
    status,
    message,
    activeSessions,
    version,
    checkStatus,
    isReady: status === 'ready',
    isWaking: status === 'waking' || status === 'checking',
    isFailed: status === 'failed',
  };
}
