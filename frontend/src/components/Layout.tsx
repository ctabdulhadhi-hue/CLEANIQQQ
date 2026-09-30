import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { useBackendStatus } from '../hooks/useBackendStatus';

export function Layout() {
  const backend = useBackendStatus();
  const location = useLocation();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [prevPath, setPrevPath] = useState(location.pathname);

  // Automatically close mobile navigation drawer when route changes
  if (prevPath !== location.pathname) {
    setPrevPath(location.pathname);
    if (mobileNavOpen) {
      setMobileNavOpen(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-[#f2f2f0] flex flex-col font-sans selection:bg-[#ff6a3d]/30 selection:text-[#ffb08a]">
      <Navbar
        backendConnected={backend.isOnline}
        activeSessions={backend.activeSessions}
        status={backend.status}
        statusMessage={backend.message}
        onCheckStatus={backend.checkStatus}
        mobileNavOpen={mobileNavOpen}
        onToggleMobileNav={() => setMobileNavOpen((prev) => !prev)}
      />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          mobileOpen={mobileNavOpen}
          onClose={() => setMobileNavOpen(false)}
        />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 bg-[#0a0a0c] min-w-0 max-w-full">
          <div className="w-full">
            <Outlet
              context={{
                backendConnected: backend.isReady,
                activeSessions: backend.activeSessions,
                backend,
              }}
            />
          </div>
        </main>
      </div>
    </div>
  );
}

export default Layout;
