import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import SynapseDashboard from '@/components/SynapseDashboard';
import ProtectedRoute from '@/components/ProtectedRoute';
import LoginPage from '@/pages/LoginPage';
import ChatView from '@/pages/ChatView';
import CajaView from '@/pages/CajaView';
import CxpView from '@/pages/CxpView';

function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      {/* Public */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/chat" replace /> : <LoginPage />}
      />

      {/* Protected — requires authentication */}
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<SynapseDashboard />}>
          <Route index element={<Navigate to="/chat" replace />} />

          {/* Each route also checks module permission */}
          <Route element={<ProtectedRoute module="chat" />}>
            <Route path="chat" element={<ChatView />} />
          </Route>

          <Route element={<ProtectedRoute module="caja" />}>
            <Route path="caja" element={<CajaView />} />
          </Route>

          <Route element={<ProtectedRoute module="cxp" />}>
            <Route path="cxp" element={<CxpView />} />
          </Route>
        </Route>
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to={isAuthenticated ? '/chat' : '/login'} replace />} />
    </Routes>
  );
}

export default App;
