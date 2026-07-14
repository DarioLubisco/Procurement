import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

interface Props {
  module?: string; // If provided, also checks module read permission
}

/**
 * Wraps routes that require authentication.
 * Redirects to /login if not authenticated or token is expired.
 * Optionally checks module-level read permission.
 */
const ProtectedRoute = ({ module }: Props) => {
  const { isAuthenticated, can } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (module && !can(module)) {
    return (
      <div className="flex items-center justify-center h-full bg-background">
        <div className="text-center p-8 max-w-sm">
          <div className="text-4xl mb-4">🔒</div>
          <h2 className="text-lg font-semibold text-foreground mb-2">Acceso restringido</h2>
          <p className="text-sm text-muted-foreground">
            No tienes permisos para acceder al módulo{' '}
            <span className="font-mono font-semibold text-primary">{module}</span>.
            Contacta al administrador.
          </p>
        </div>
      </div>
    );
  }

  return <Outlet />;
};

export default ProtectedRoute;
