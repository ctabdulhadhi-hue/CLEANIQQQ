import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  Table2,
  Wand2,
  BarChart3,
  History,
  ShieldAlert,
} from 'lucide-react';

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Upload', path: '/upload', icon: UploadCloud },
  { name: 'Dataset', path: '/dataset', icon: Table2 },
  { name: 'Cleaning', path: '/cleaning', icon: Wand2 },
  { name: 'Visualization', path: '/visualization', icon: BarChart3 },
  { name: 'History', path: '/history', icon: History },
];

export function Sidebar() {
  return (
    <aside className="w-64 border-r border-[rgba(255,255,255,0.08)] bg-[#0c0c0e] flex flex-col justify-between p-4 shrink-0">
      <div>
        <div className="text-[11px] font-semibold tracking-wider text-[#8a8a86] uppercase px-3 mb-3 pt-2">
          Navigation
        </div>
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `sidebar-nav-item flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium ${
                    isActive
                      ? 'bg-[#ff6a3d]/12 text-[#ff6a3d] border border-[#ff6a3d]/25 font-semibold'
                      : 'text-[#8a8a86] hover:text-[#f2f2f0] hover:bg-white/[0.04] border border-transparent'
                  }`
                }
              >
                <Icon className="w-4 h-4" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Safety Notice Box in Sidebar */}
      <div className="p-3.5 rounded-[12px] bg-white/[0.03] border border-[rgba(255,255,255,0.08)] text-xs text-[#8a8a86] space-y-2">
        <div className="flex items-center gap-1.5 text-[#f2f2f0] font-semibold text-[11px]">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
          <span>Strict Guardrails</span>
        </div>
        <p className="text-[11px] leading-relaxed text-[#8a8a86]">
          CleanIQ strictly previews every operation before applying changes.
        </p>
      </div>
    </aside>
  );
}
