import React, { createContext, useContext, useEffect, useState, useRef, ReactNode } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from './AuthContext'
import type { WebSocketMessage, NotificationMessage } from '@/types'

interface WebSocketContextType {
  isConnected: boolean
  connectionState: 'disconnected' | 'connecting' | 'connected' | 'authenticated' | 'error'
  sendMessage: (message: any) => void
  subscribe: (types: string[]) => void
  notifications: NotificationMessage[]
  clearNotifications: () => void
  lastMessage: WebSocketMessage | null
  reconnect: () => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

interface WebSocketProviderProps {
  children: ReactNode
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const { user, isAuthenticated } = useAuth()
  const [isConnected, setIsConnected] = useState(false)
  const [connectionState, setConnectionState] = useState<'disconnected' | 'connecting' | 'connected' | 'authenticated' | 'error'>('disconnected')
  const [notifications, setNotifications] = useState<NotificationMessage[]>([])
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const sessionIdRef = useRef<string>(`session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)

  const maxReconnectAttempts = 5
  const reconnectDelay = 1000

  // Clear notifications
  const clearNotifications = () => {
    setNotifications([])
  }

  // Send message through WebSocket
  const sendMessage = (message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  // Subscribe to specific notification types
  const subscribe = (types: string[]) => {
    sendMessage({
      type: 'subscribe',
      notification_types: types
    })
  }

  // Connect to WebSocket
  const connect = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return // Already connected
    }

    try {
      setConnectionState('connecting')
      
      const wsUrl = new URL('/chat/stream/' + sessionIdRef.current, window.location.origin)
      wsUrl.protocol = wsUrl.protocol === 'https:' ? 'wss:' : 'ws:'
      
      // Add auth token if available
      const token = localStorage.getItem('auth_token')
      if (token) {
        wsUrl.searchParams.set('token', token)
      }
      
      // Add client info
      const clientInfo = {
        user_agent: navigator.userAgent,
        timestamp: new Date().toISOString(),
        url: window.location.href
      }
      wsUrl.searchParams.set('client_info', JSON.stringify(clientInfo))

      wsRef.current = new WebSocket(wsUrl.toString())

      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setConnectionState('connected')
        reconnectAttemptsRef.current = 0

        // Authenticate if user is logged in
        if (isAuthenticated && token) {
          sendMessage({
            type: 'authenticate',
            token: token
          })
        }
      }

      wsRef.current.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(data)

          // Handle different message types
          switch (data.category) {
            case 'system':
              handleSystemMessage(data)
              break
            case 'notification':
              handleNotificationMessage(data)
              break
            case 'chat':
              handleChatMessage(data)
              break
            case 'approval':
              handleApprovalMessage(data)
              break
            default:
              console.log('Received message:', data)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        setIsConnected(false)
        setConnectionState('disconnected')
        
        // Attempt to reconnect unless it was a clean close
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          scheduleReconnect()
        }
      }

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionState('error')
      }

    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      setConnectionState('error')
    }
  }

  // Handle system messages
  const handleSystemMessage = (data: WebSocketMessage) => {
    switch (data.type) {
      case 'connection_established':
        console.log('WebSocket connection established')
        break
      case 'authentication_success':
        console.log('WebSocket authenticated successfully')
        setConnectionState('authenticated')
        toast.success('Real-time connection established')
        break
      case 'authentication_failed':
        console.error('WebSocket authentication failed')
        toast.error('Failed to authenticate real-time connection')
        break
      case 'pong':
        // Handle ping/pong for connection health
        break
      case 'error':
        toast.error(data.data.message || 'WebSocket error occurred')
        break
      default:
        console.log('System message:', data)
    }
  }

  // Handle notification messages
  const handleNotificationMessage = (data: WebSocketMessage) => {
    const notification: NotificationMessage = {
      type: data.type as any,
      data: data.data,
      priority: data.data.priority || 'medium',
      timestamp: data.timestamp,
      session_id: data.session_id,
      id: data.message_id
    }

    setNotifications(prev => [...prev, notification])

    // Show toast for high priority notifications
    if (notification.priority === 'high' || notification.priority === 'critical') {
      const message = notification.data.message || `${notification.type} notification`
      if (notification.priority === 'critical') {
        toast.error(message)
      } else {
        toast(message, { icon: '🔔' })
      }
    }
  }

  // Handle chat messages
  const handleChatMessage = (data: WebSocketMessage) => {
    console.log('Chat message received:', data)
    // Chat messages are handled by the chat components directly
  }

  // Handle approval messages
  const handleApprovalMessage = (data: WebSocketMessage) => {
    const message = data.data.message || 'New approval notification'
    toast(message, { 
      icon: '📋',
      duration: 6000 
    })
  }

  // Schedule reconnection
  const scheduleReconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }

    const delay = reconnectDelay * Math.pow(2, reconnectAttemptsRef.current) // Exponential backoff
    reconnectAttemptsRef.current++

    console.log(`Scheduling WebSocket reconnect attempt ${reconnectAttemptsRef.current} in ${delay}ms`)

    reconnectTimeoutRef.current = setTimeout(() => {
      connect()
    }, delay)
  }

  // Manual reconnect function
  const reconnect = () => {
    if (wsRef.current) {
      wsRef.current.close()
    }
    reconnectAttemptsRef.current = 0
    connect()
  }

  // Send periodic ping to keep connection alive
  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (isConnected) {
        sendMessage({ type: 'ping' })
      }
    }, 30000) // Ping every 30 seconds

    return () => clearInterval(pingInterval)
  }, [isConnected])

  // Connect when user authenticates
  useEffect(() => {
    if (isAuthenticated) {
      connect()
    } else {
      // Close connection when user logs out
      if (wsRef.current) {
        wsRef.current.close(1000, 'User logged out')
      }
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting')
      }
    }
  }, [isAuthenticated])

  // Handle page visibility changes
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && isAuthenticated && !isConnected) {
        // Reconnect when page becomes visible
        reconnect()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [isAuthenticated, isConnected])

  // Handle online/offline events
  useEffect(() => {
    const handleOnline = () => {
      if (isAuthenticated && !isConnected) {
        reconnect()
      }
    }

    const handleOffline = () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [isAuthenticated, isConnected])

  const value: WebSocketContextType = {
    isConnected,
    connectionState,
    sendMessage,
    subscribe,
    notifications,
    clearNotifications,
    lastMessage,
    reconnect,
  }

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocket(): WebSocketContextType {
  const context = useContext(WebSocketContext)
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

// Utility hook for listening to specific message types
export function useWebSocketMessage(
  messageType: string,
  callback: (data: WebSocketMessage) => void,
  deps: React.DependencyList = []
) {
  const { lastMessage } = useWebSocket()

  useEffect(() => {
    if (lastMessage && lastMessage.type === messageType) {
      callback(lastMessage)
    }
  }, [lastMessage, messageType, callback, ...deps])
}