import { Outlet, NavLink } from 'react-router-dom';
import { MessageSquare, DollarSign, Wallet, Moon, Sun, LogOut } from 'lucide-react';
import { useDarkMode } from '@/hooks/useDarkMode';
import { useAuth } from '@/hooks/useAuth';

const navItems = [
  { name: 'Chat', path: '/chat', icon: MessageSquare, module: 'chat' },
  { name: 'Caja', path: '/caja', icon: Wallet, module: 'caja' },
  { name: 'CxP', path: '/cxp', icon: DollarSign, module: 'cxp' },
];

const SynapseDashboard = () => {
  const { isDark, toggle } = useDarkMode();
  const { user, logout, can } = useAuth();

  // Initials from nombre
  const initials = user?.nombre
    ? user.nombre.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
    : '??';

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 border-r border-border bg-card flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center px-5 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold text-sm shadow-sm">
              S
            </div>
            <div>
              <span className="text-sm font-bold text-foreground tracking-tight block leading-none">Synapse</span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-widest">Dashboard</span>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest px-3 py-2">
            Módulos
          </p>
          {navItems.map(item => {
            const hasAccess = can(item.module);
            return (
              <NavLink
                key={item.name}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                    !hasAccess
                      ? 'text-muted-foreground/40 cursor-not-allowed pointer-events-none'
                      : isActive
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                  }`
                }
              >
                <item.icon className="w-4 h-4 flex-shrink-0" />
                <span>{item.name}</span>
                {!hasAccess && (
                  <span className="ml-auto text-[9px] font-semibold uppercase tracking-wider text-muted-foreground/50">
                    🔒
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* User Profile Section */}
        {user && (
          <div className="p-3 border-t border-border">
            <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-secondary/50">
              {/* Avatar */}
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold flex-shrink-0">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate leading-tight">{user.nombre}</p>
                <p className="text-[11px] text-muted-foreground truncate">@{user.username}</p>
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-1 mt-2">
              <button
                onClick={toggle}
                title={isDark ? 'Modo claro' : 'Modo oscuro'}
                className="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-muted-foreground hover:bg-secondary hover:text-foreground transition-all"
              >
                {isDark ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
                <span>{isDark ? 'Claro' : 'Oscuro'}</span>
              </button>
              <button
                onClick={logout}
                title="Cerrar sesión"
                className="p-2 rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-all"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden flex flex-col">
        <Outlet />
      </main>
    </div>
  );
};

export default SynapseDashboard;
