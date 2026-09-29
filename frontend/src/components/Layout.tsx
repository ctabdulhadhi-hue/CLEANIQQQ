import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { useBackendStatus } from '../hooks/useBackendStatus';

export function Layout() {
  const backend = useBackendStatus();

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-[#f2f2f0] flex flex-col font-sans selection:bg-[#ff6a3d]/30 selection:text-[#ffb08a]">
      <Navbar
        backendConnected={backend.isOnline}
        activeSessions={backend.activeSessions}
        status={backend.status}
        statusMessage={backend.message}
        onCheckStatus={backend.checkStatus}
      />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-8 bg-[#0a0a0c]">
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
