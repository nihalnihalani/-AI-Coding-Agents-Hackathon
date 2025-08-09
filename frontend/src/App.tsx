import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'

// Components
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'

// Pages
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ChatPage from './pages/ChatPage'
import OnboardingPage from './pages/OnboardingPage'
import ApprovalsPage from './pages/ApprovalsPage'
import ProfilePage from './pages/ProfilePage'
import SettingsPage from './pages/SettingsPage'
import LoadingPage from './pages/LoadingPage'

function App() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <LoadingPage />
  }

  return (
    <Routes>
      {/* Public routes */}
      <Route 
        path="/login" 
        element={
          user ? <Navigate to="/dashboard" replace /> : <LoginPage />
        } 
      />
      
      {/* Protected routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="onboarding" element={<OnboardingPage />} />
        <Route 
          path="approvals" 
          element={
            <ProtectedRoute requiredRole="manager">
              <ApprovalsPage />
            </ProtectedRoute>
          } 
        />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      
      {/* Catch all - redirect to dashboard if authenticated, login if not */}
      <Route 
        path="*" 
        element={
          <Navigate to={user ? "/dashboard" : "/login"} replace />
        } 
      />
    </Routes>
  )
}

export default App