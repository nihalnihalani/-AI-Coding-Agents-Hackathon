// API client configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Auth token management
let authToken: string | null = localStorage.getItem('auth_token')

export const setAuthToken = (token: string | null) => {
  authToken = token
  if (token) {
    localStorage.setItem('auth_token', token)
  } else {
    localStorage.removeItem('auth_token')
  }
}

export const getAuthToken = () => authToken

// Base fetch wrapper
const apiFetch = async (endpoint: string, options: RequestInit = {}) => {
  const url = `${API_BASE_URL}${endpoint}`
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `API Error: ${response.status}`)
  }
  
  return response.json()
}

// Auth API
export const authApi = {
  login: async (credentials: { email: string; password: string }) => {
    const response = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    })
    
    if (response.access_token) {
      setAuthToken(response.access_token)
    }
    
    return response
  },
  
  logout: async () => {
    setAuthToken(null)
    return { success: true }
  },
  
  getCurrentUser: async () => {
    return apiFetch('/api/auth/me')
  },
}

// Chat API
export const chatApi = {
  sendMessage: async (message: string, sessionId?: string) => {
    return apiFetch('/api/chat/message', {
      method: 'POST',
      body: JSON.stringify({
        message,
        session_id: sessionId,
      }),
    })
  },
  
  getHistory: async (sessionId: string) => {
    return apiFetch(`/api/chat/history/${sessionId}`)
  },
  
  getSuggestions: async (sessionId: string) => {
    return apiFetch(`/api/chat/suggestions/${sessionId}`)
  },
}

// Dashboard API
export const dashboardApi = {
  getStats: async () => {
    return apiFetch('/api/dashboard/stats')
  },
  
  getActivity: async () => {
    return apiFetch('/api/dashboard/activity')
  },
}

// Onboarding API
export const onboardingApi = {
  getProgress: async (sessionId: string) => {
    return apiFetch(`/api/onboarding/progress/${sessionId}`)
  },
  
  getPlan: async (sessionId: string) => {
    return apiFetch(`/api/onboarding/plan/${sessionId}`)
  },
  
  uploadDocument: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    
    return apiFetch('/api/onboarding/upload', {
      method: 'POST',
      headers: {}, // Let browser set content-type for FormData
      body: formData as any,
    })
  },
}

// Calendar API
export const calendarApi = {
  getEvents: async (days: number = 7) => {
    return apiFetch(`/api/calendar/events?days=${days}`)
  },
  
  scheduleEvent: async (eventData: any) => {
    return apiFetch('/api/calendar/schedule', {
      method: 'POST',
      body: JSON.stringify(eventData),
    })
  },
}

// Settings API
export const settingsApi = {
  getUserSettings: async () => {
    return apiFetch('/api/settings/user')
  },
  
  updateUserSettings: async (settings: any) => {
    return apiFetch('/api/settings/user', {
      method: 'PUT',
      body: JSON.stringify(settings),
    })
  },
}

// Approvals API
export const approvalsApi = {
  getPending: async () => {
    return apiFetch('/api/approvals/pending')
  },
  
  approve: async (id: string) => {
    return apiFetch(`/api/approvals/${id}/approve`, {
      method: 'POST',
    })
  },
  
  reject: async (id: string, reason?: string) => {
    return apiFetch(`/api/approvals/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    })
  },
}