import { useEffect, useState, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { checkBackendHealth } from '../services/api';

// Cache in module scope to prevent status dot flickering on route changes
let cachedBackendConnected: boolean | null = null;
let cachedActiveSessions = 0;

// Render free tier sleeps after inactivity. Wake-up takes ~30-60s.
// We retry aggressively before declaring "offline".
const WAKE_UP_RETRY_DELAYS = [2000, 3000, 4000, 5000, 8000, 10000, 15000, 20000]; // ~67s total
const POLL_INTERVAL = 10000; // Normal polling once connected

export function Layout() {
  const [backendConnected, setBackendConnected] = useState<boolean | null>(cachedBackendConnected);
  const [activeSessions, setActiveSessions] = useState<number>(cachedActiveSessions);
  const [wakingUp, setWakingUp] = useState(false);

  const markOnline = useCallback((sessions: number) => {
    cachedBackendConnected = true;
    cachedActiveSessions = sessions;
    setBackendConnected(true);
    setActiveSessions(sessions);
    setWakingUp(false);
  }, []);

  const markOffline = useCallback(() => {
    cachedBackendConnected = false;
    setBackendConnected(false);
    setWakingUp(false);
  }, []);

  useEffect(() => {
    let isMounted = true;
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    // Try a single health check with a short timeout
    const singleCheck = async (): Promise<boolean> => {
      try {
        const data = await checkBackendHealth(5000);
        if (isMounted) markOnline(data.active_sessions || 0);
        return true;
      } catch {
        return false;
      }
    };

    // Wake-up sequence: retry with increasing delays
    const wakeUpSequence = async () => {
      // If we aren't already marked online from cache, show waking up
      if (cachedBackendConnected !== true && isMounted) {
        setWakingUp(true);
      }

      // First attempt
      if (await singleCheck()) return;

      // Backend didn't respond immediately — retry through delays
      for (const delay of WAKE_UP_RETRY_DELAYS) {
        if (!isMounted) return;
        await new Promise((r) => setTimeout(r, delay));
        if (!isMounted) return;
        if (await singleCheck()) return;
      }

      // If still not reachable after ~67s, show offline but keep background polling
      if (isMounted) markOffline();
    };

    // Start with wake-up sequence
    wakeUpSequence().finally(() => {
      if (!isMounted) return;
      // Keep polling continuously so if backend wakes up later, it reconnects automatically
      pollTimer = setInterval(async () => {
        if (!isMounted) return;
        const ok = await singleCheck();
        if (!ok && isMounted && cachedBackendConnected) {
          // Retry once quickly before marking offline
          await new Promise((r) => setTimeout(r, 2000));
          if (!isMounted) return;
          const retryOk = await singleCheck();
          if (!retryOk && isMounted) markOffline();
        }
      }, POLL_INTERVAL);
    });

    return () => {
      isMounted = false;
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [markOnline, markOffline]);

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-[#f2f2f0] flex flex-col font-sans selection:bg-[#ff6a3d]/30 selection:text-[#ffb08a]">
      <Navbar backendConnected={backendConnected} activeSessions={activeSessions} wakingUp={wakingUp} />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-8 bg-[#0a0a0c]">
          <div className="w-full">
            <Outlet context={{ backendConnected, activeSessions }} />
          </div>
        </main>
      </div>
    </div>
  );
}

export default Layout;

