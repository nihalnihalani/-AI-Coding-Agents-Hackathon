import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { authApi, setAuthToken } from '@/lib/api'
import type { User, LoginRequest } from '@/types'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => Promise<void>
  updateUser: (userData: Partial<User>) => void
  checkPermission: (permission: string) => boolean
  hasRole: (role: string) => boolean
  refreshAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()

  const isAuthenticated = !!user

  // Check if user has specific permission
  const checkPermission = (permission: string): boolean => {
    if (!user) return false
    
    // Admin wildcard permission
    if (user.permissions.includes('*')) return true
    
    // Exact permission match
    if (user.permissions.includes(permission)) return true
    
    // Wildcard permission matching (e.g., "onboarding:*" matches "onboarding:read")
    return user.permissions.some(userPerm => {
      if (userPerm.endsWith(':*')) {
        const permissionPrefix = userPerm.slice(0, -1) // Remove the "*"
        return permission.startsWith(permissionPrefix)
      }
      return false
    })
  }

  // Check if user has specific role
  const hasRole = (role: string): boolean => {
    return user?.role === role
  }

  // Login function
  const login = async (credentials: LoginRequest): Promise<void> => {
    try {
      setIsLoading(true)
      const response = await authApi.login(credentials)
      
      // Set token and user data
      setAuthToken(response.access_token)
      setUser(response.user_info)
      
      toast.success(`Welcome back, ${response.user_info.full_name}!`)
      navigate('/dashboard')
    } catch (error: any) {
      console.error('Login error:', error)
      const message = error.response?.data?.detail || 'Login failed. Please check your credentials.'
      toast.error(message)
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  // Logout function
  const logout = async (): Promise<void> => {
    try {
      await authApi.logout()
    } catch (error) {
      console.error('Logout error:', error)
      // Continue with logout even if API call fails
    } finally {
      setAuthToken(null)
      setUser(null)
      navigate('/login')
      toast.success('Logged out successfully')
    }
  }

  // Update user data
  const updateUser = (userData: Partial<User>): void => {
    if (user) {
      setUser({ ...user, ...userData })
    }
  }

  // Refresh authentication state
  const refreshAuth = async (): Promise<void> => {
    try {
      const userData = await authApi.getCurrentUser()
      setUser(userData)
    } catch (error) {
      console.error('Auth refresh error:', error)
      setAuthToken(null)
      setUser(null)
    }
  }

  // Initialize authentication state
  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('auth_token')
      
      if (!token) {
        setIsLoading(false)
        return
      }

      try {
        // Validate token and get user data
        setAuthToken(token)
        const userData = await authApi.getCurrentUser()
        setUser(userData)
      } catch (error) {
        console.error('Auth initialization error:', error)
        // Token is invalid, clear it
        setAuthToken(null)
        localStorage.removeItem('auth_token')
      } finally {
        setIsLoading(false)
      }
    }

    initializeAuth()
  }, [])

  // Auto-refresh token before expiry
  useEffect(() => {
    if (!user || !isAuthenticated) return

    const refreshInterval = setInterval(async () => {
      try {
        const response = await authApi.refreshToken()
        setAuthToken(response.access_token)
      } catch (error) {
        console.error('Token refresh error:', error)
        // If refresh fails, logout user
        await logout()
      }
    }, 15 * 60 * 1000) // Refresh every 15 minutes

    return () => clearInterval(refreshInterval)
  }, [isAuthenticated, user])

  // Handle authentication errors globally
  useEffect(() => {
    const handleAuthError = () => {
      setUser(null)
      setAuthToken(null)
      navigate('/login')
    }

    // Listen for auth errors from API interceptors
    window.addEventListener('auth-error', handleAuthError)
    return () => window.removeEventListener('auth-error', handleAuthError)
  }, [navigate])

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated,
    login,
    logout,
    updateUser,
    checkPermission,
    hasRole,
    refreshAuth,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Helper hook for role-based access
export function useRequiredRole(requiredRole: string) {
  const { user, hasRole } = useAuth()
  return user && hasRole(requiredRole)
}

// Helper hook for permission-based access
export function useRequiredPermission(requiredPermission: string) {
  const { user, checkPermission } = useAuth()
  return user && checkPermission(requiredPermission)
}