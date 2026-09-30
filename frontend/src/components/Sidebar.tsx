import { useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  Table2,
  Wand2,
  BarChart3,
  History,
  ShieldAlert,
  X,
} from 'lucide-react';

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Upload', path: '/upload', icon: UploadCloud },
  { name: 'Dataset', path: '/dataset', icon: Table2 },
  { name: 'Cleaning', path: '/cleaning', icon: Wand2 },
  { name: 'Visualization', path: '/visualization', icon: BarChart3 },
  { name: 'History', path: '/history', icon: History },
];

export interface SidebarProps {
  mobileOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ mobileOpen = false, onClose }: SidebarProps) {
  // Handle Escape key and body scroll lock for mobile drawer
  useEffect(() => {
    if (!mobileOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [mobileOpen, onClose]);

  const renderNavList = (isMobile = false) => (
    <nav className="space-y-1">
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.path}
            to={item.path}
            onClick={() => {
              if (isMobile && onClose) {
                onClose();
              }
            }}
            className={({ isActive }) =>
              `sidebar-nav-item flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-[#ff6a3d]/12 text-[#ff6a3d] border border-[#ff6a3d]/25 font-semibold'
                  : 'text-[#8a8a86] hover:text-[#f2f2f0] hover:bg-white/[0.04] border border-transparent'
              }`
            }
          >
            <Icon className="w-4 h-4 shrink-0" />
            <span>{item.name}</span>
          </NavLink>
        );
      })}
    </nav>
  );

  const renderGuardrailsNotice = () => (
    <div className="p-3.5 rounded-[12px] bg-white/[0.03] border border-[rgba(255,255,255,0.08)] text-xs text-[#8a8a86] space-y-2">
      <div className="flex items-center gap-1.5 text-[#f2f2f0] font-semibold text-[11px]">
        <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />
        <span>Strict Guardrails</span>
      </div>
      <p className="text-[11px] leading-relaxed text-[#8a8a86]">
        CleanIQ strictly previews every operation before applying changes.
      </p>
    </div>
  );

  return (
    <>
      {/* ─── Desktop Sidebar (MD and above) ───────────────────────────────── */}
      <aside className="hidden md:flex w-64 border-r border-[rgba(255,255,255,0.08)] bg-[#0c0c0e] flex-col justify-between p-4 shrink-0">
        <div>
          <div className="text-[11px] font-semibold tracking-wider text-[#8a8a86] uppercase px-3 mb-3 pt-2">
            Navigation
          </div>
          {renderNavList(false)}
        </div>
        {renderGuardrailsNotice()}
      </aside>

      {/* ─── Mobile Drawer Backdrop & Drawer (< 768px) ────────────────────── */}
      {mobileOpen && (
        <div
          id="mobile-drawer-backdrop"
          className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 md:hidden transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        id="mobile-navigation-drawer"
        aria-label="Mobile Navigation"
        aria-hidden={!mobileOpen}
        className={`fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] bg-[#0c0c0e] border-r border-[rgba(255,255,255,0.12)] p-4 flex flex-col justify-between shadow-2xl transition-transform duration-300 ease-in-out md:hidden ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full pointer-events-none'
        }`}
      >
        <div>
          <div className="flex items-center justify-between px-2 pt-1 mb-4 pb-3 border-b border-white/[0.08]">
            <div className="flex items-center gap-2.5">
              <img src="/logo-dark-bg.svg" alt="CleanIQ" className="h-6 w-auto object-contain" />
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-[#ff6a3d]/10 text-[#ffb08a] border border-[#ff6a3d]/25">
                Navigation
              </span>
            </div>
            <button
              type="button"
              id="mobile-drawer-close-btn"
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#8a8a86] hover:text-white hover:bg-white/[0.06] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6a3d]"
              aria-label="Close navigation drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          {renderNavList(true)}
        </div>
        {renderGuardrailsNotice()}
      </aside>
    </>
  );
}

export default Sidebar;
