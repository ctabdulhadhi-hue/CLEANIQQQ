import { useState, useEffect, useCallback, useRef } from 'react';
import { checkBackendHealth, type HealthResponse } from '../services/api';

export type BackendStatus = 'checking' | 'waking' | 'ready' | 'failed';

interface UseBackendStatusReturn {
  status: BackendStatus;
  message: string;
  activeSessions: number;
  checkStatus: () => void;
  isReady: boolean;
  isWaking: boolean;
  isFailed: boolean;
}

const MAX_WAKE_TIME_MS = 90_000; // 90 seconds max wait for cold start
const POLL_INTERVAL_MS = 3_000;  // Poll every 3 seconds

export function useBackendStatus(): UseBackendStatusReturn {
  const [status, setStatus] = useState<BackendStatus>('checking');
  const [activeSessions, setActiveSessions] = useState<number>(0);
  const [message, setMessage] = useState<string>('Checking backend status...');

  const startTimeRef = useRef<number>(Date.now());
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isCheckingRef = useRef<boolean>(false);

  const performCheck = useCallback(async () => {
    if (isCheckingRef.current) return;
    isCheckingRef.current = true;

    try {
      // 4-second timeout per attempt
      const res: HealthResponse = await checkBackendHealth(4000);
      if (res && (res.status === 'ok' || res.status === 'healthy' || (res as any).ok)) {
        setStatus('ready');
        setActiveSessions(res.active_sessions || 0);
        setMessage('Backend Online');
        isCheckingRef.current = false;
        return true;
      } else {
        const elapsed = Date.now() - startTimeRef.current;
        if (elapsed >= MAX_WAKE_TIME_MS) {
          setStatus('failed');
          setMessage("Backend didn't respond");
        } else {
          setStatus('waking');
          setMessage('Backend is starting (free-tier cold start, usually 20-45 seconds)');
        }
      }
    } catch {
      // Failed this ping
      const elapsed = Date.now() - startTimeRef.current;
      if (elapsed >= MAX_WAKE_TIME_MS) {
        setStatus('failed');
        setMessage("Backend didn't respond");
      } else {
        setStatus('waking');
        setMessage('Backend is starting (free-tier cold start, usually 20-45 seconds)');
      }
    } finally {
      isCheckingRef.current = false;
    }
    return false;
  }, []);

  const startPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    startTimeRef.current = Date.now();
    setStatus('checking');
    setMessage('Connecting to backend...');

    // Immediate first ping
    performCheck();

    timerRef.current = setInterval(async () => {
      const isSuccess = await performCheck();
      if (isSuccess && timerRef.current) {
        // Once ready, slow down polling to maintain warm connection every 15s
        clearInterval(timerRef.current);
        timerRef.current = setInterval(performCheck, 15000);
      }
    }, POLL_INTERVAL_MS);
  }, [performCheck]);

  const checkStatus = useCallback(() => {
    startPolling();
  }, [startPolling]);

  useEffect(() => {
    startPolling();
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [startPolling]);

  return {
    status,
    message,
    activeSessions,
    checkStatus,
    isReady: status === 'ready',
    isWaking: status === 'waking' || status === 'checking',
    isFailed: status === 'failed',
  };
}
