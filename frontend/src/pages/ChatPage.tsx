import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  PaperAirplaneIcon, 
  MicrophoneIcon, 
  StopIcon,
  DocumentArrowUpIcon,
  TrashIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/react/24/outline'
import { useAuth } from '@/contexts/AuthContext'
import { useWebSocket, useWebSocketMessage } from '@/contexts/WebSocketContext'
import { chatApi } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import type { ChatMessage, ChatRequest } from '@/types'

export default function ChatPage() {
  const { user } = useAuth()
  const { sendMessage, isConnected } = useWebSocket()
  const queryClient = useQueryClient()
  
  const [message, setMessage] = useState('')
  const [sessionId] = useState(() => `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  const [isTyping, setIsTyping] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Load chat history
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['chat-history', sessionId],
    queryFn: () => chatApi.getHistory(sessionId, 100),
    refetchOnWindowFocus: false,
  })

  // Load suggestions
  const { data: suggestionsData } = useQuery({
    queryKey: ['chat-suggestions', sessionId],
    queryFn: () => chatApi.getSuggestions(sessionId),
    refetchOnWindowFocus: false,
  })

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: (request: ChatRequest) => chatApi.sendMessage(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-history', sessionId] })
      queryClient.invalidateQueries({ queryKey: ['chat-suggestions', sessionId] })
    },
    onError: (error) => {
      toast.error('Failed to send message')
    }
  })

  // Clear history mutation
  const clearHistoryMutation = useMutation({
    mutationFn: () => chatApi.clearHistory(sessionId, true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-history', sessionId] })
      toast.success('Chat history cleared')
    }
  })

  const messages: ChatMessage[] = historyData?.data?.conversation_history || []
  const suggestions: string[] = suggestionsData?.data?.suggestions || []

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Listen for WebSocket chat messages
  useWebSocketMessage('chat_response', (data) => {
    queryClient.invalidateQueries({ queryKey: ['chat-history', sessionId] })
    queryClient.invalidateQueries({ queryKey: ['chat-suggestions', sessionId] })
  })

  // Handle typing indicators
  const handleTyping = () => {
    if (!isConnected) return

    if (!isTyping) {
      setIsTyping(true)
      sendMessage({ type: 'typing_indicator', typing: true })
    }

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current)
    }

    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false)
      sendMessage({ type: 'typing_indicator', typing: false })
    }, 1000)
  }

  // Send message
  const handleSendMessage = async (messageText?: string) => {
    const textToSend = messageText || message.trim()
    if (!textToSend || sendMessageMutation.isPending) return

    setMessage('')
    setIsTyping(false)
    
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current)
    }

    try {
      await sendMessageMutation.mutateAsync({
        message: textToSend,
        session_id: sessionId,
        context: {
          user_id: user?.user_id,
          timestamp: new Date().toISOString()
        }
      })
    } catch (error) {
      console.error('Error sending message:', error)
    }
  }

  // Handle Enter key
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Handle suggestion click
  const handleSuggestionClick = (suggestion: string) => {
    handleSendMessage(suggestion)
  }

  // Voice recording (placeholder for future Vapi integration)
  const toggleRecording = () => {
    setIsRecording(!isRecording)
    if (!isRecording) {
      toast.success('Voice recording started')
      // TODO: Integrate with Vapi
    } else {
      toast.success('Voice recording stopped')
      // TODO: Process voice input
    }
  }

  const getMessageIcon = (role: string, llmUsed?: string) => {
    if (role === 'user') {
      return (
        <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center">
          <span className="text-white text-sm font-medium">
            {user?.full_name?.charAt(0) || 'U'}
          </span>
        </div>
      )
    } else {
      return (
        <div className="w-8 h-8 bg-gradient-to-br from-secondary-600 to-secondary-800 rounded-full flex items-center justify-center">
          <span className="text-white text-sm font-bold">A</span>
        </div>
      )
    }
  }

  const getLLMBadge = (llmUsed?: string) => {
    if (!llmUsed) return null
    
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        llmUsed === 'gemini' ? 'bg-blue-100 text-blue-800' :
        llmUsed === 'claude' ? 'bg-purple-100 text-purple-800' :
        'bg-secondary-100 text-secondary-800'
      }`}>
        {llmUsed}
      </span>
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-10rem)] max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <ChatBubbleLeftRightIcon className="h-8 w-8 text-primary-600" />
          <div>
            <h1 className="text-2xl font-bold text-secondary-900">Chat with Aura</h1>
            <p className="text-secondary-600">Your AI onboarding assistant</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-sm ${
            isConnected ? 'bg-success-100 text-success-800' : 'bg-danger-100 text-danger-800'
          }`}>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success-500' : 'bg-danger-500'}`} />
            <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
          
          {messages.length > 0 && (
            <button
              onClick={() => clearHistoryMutation.mutate()}
              className="btn btn-ghost btn-sm"
              disabled={clearHistoryMutation.isPending}
            >
              <TrashIcon className="h-4 w-4 mr-1" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 bg-white rounded-lg shadow-sm border border-secondary-200 flex flex-col">
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {historyLoading ? (
            <div className="flex justify-center items-center h-32">
              <div className="w-8 h-8 loading-spinner border-primary-600" />
            </div>
          ) : messages.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 mx-auto mb-4 bg-secondary-100 rounded-full flex items-center justify-center">
                <ChatBubbleLeftRightIcon className="h-8 w-8 text-secondary-400" />
              </div>
              <h3 className="text-lg font-medium text-secondary-900 mb-2">Start a conversation</h3>
              <p className="text-secondary-600 mb-6">Ask me anything about your onboarding process!</p>
              
              {suggestions.length > 0 && (
                <div className="max-w-md mx-auto">
                  <p className="text-sm text-secondary-600 mb-3">Try these suggestions:</p>
                  <div className="grid gap-2">
                    {suggestions.slice(0, 3).map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => handleSuggestionClick(suggestion)}
                        className="text-left p-3 bg-secondary-50 hover:bg-secondary-100 rounded-lg text-sm text-secondary-700 transition-colors"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <>
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex space-x-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role !== 'user' && (
                    <div className="flex-shrink-0">
                      {getMessageIcon(msg.role, msg.llm_used)}
                    </div>
                  )}
                  
                  <div className={`max-w-xs lg:max-w-md xl:max-w-lg ${msg.role === 'user' ? 'order-1' : 'order-2'}`}>
                    <div className={`rounded-lg px-4 py-2 ${
                      msg.role === 'user' 
                        ? 'bg-primary-600 text-white' 
                        : 'bg-secondary-100 text-secondary-900'
                    }`}>
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    </div>
                    
                    <div className={`flex items-center space-x-2 mt-1 text-xs text-secondary-500 ${
                      msg.role === 'user' ? 'justify-end' : 'justify-start'
                    }`}>
                      <span>
                        {formatDistanceToNow(new Date(msg.timestamp), { addSuffix: true })}
                      </span>
                      {msg.llm_used && getLLMBadge(msg.llm_used)}
                      {msg.intent && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-secondary-100 text-secondary-600">
                          {msg.intent}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {msg.role === 'user' && (
                    <div className="flex-shrink-0 order-2">
                      {getMessageIcon(msg.role)}
                    </div>
                  )}
                </div>
              ))}
              
              {sendMessageMutation.isPending && (
                <div className="flex space-x-3 justify-start">
                  <div className="flex-shrink-0">
                    {getMessageIcon('assistant')}
                  </div>
                  <div className="max-w-xs lg:max-w-md">
                    <div className="bg-secondary-100 rounded-lg px-4 py-2">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" />
                        <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                        <div className="w-2 h-2 bg-secondary-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggestions */}
        {suggestions.length > 0 && messages.length > 0 && (
          <div className="border-t border-secondary-200 p-4">
            <p className="text-sm text-secondary-600 mb-2">Suggested questions:</p>
            <div className="flex flex-wrap gap-2">
              {suggestions.slice(0, 4).map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="text-xs bg-secondary-50 hover:bg-secondary-100 text-secondary-700 px-3 py-1 rounded-full transition-colors"
                  disabled={sendMessageMutation.isPending}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-secondary-200 p-4">
          <div className="flex items-end space-x-3">
            <div className="flex-1">
              <textarea
                ref={inputRef}
                value={message}
                onChange={(e) => {
                  setMessage(e.target.value)
                  handleTyping()
                }}
                onKeyPress={handleKeyPress}
                placeholder="Type your message... (Shift+Enter for new line)"
                className="w-full resize-none border border-secondary-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                rows={message.split('\n').length}
                disabled={sendMessageMutation.isPending}
              />
            </div>
            
            <div className="flex space-x-2">
              <button
                type="button"
                onClick={toggleRecording}
                className={`btn btn-sm ${isRecording ? 'bg-danger-600 text-white' : 'btn-ghost'}`}
                title={isRecording ? 'Stop recording' : 'Start voice recording'}
              >
                {isRecording ? (
                  <StopIcon className="h-4 w-4" />
                ) : (
                  <MicrophoneIcon className="h-4 w-4" />
                )}
              </button>
              
              <button
                type="button"
                onClick={() => handleSendMessage()}
                disabled={!message.trim() || sendMessageMutation.isPending}
                className="btn btn-primary btn-sm"
              >
                <PaperAirplaneIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
          
          <div className="flex items-center justify-between mt-2 text-xs text-secondary-500">
            <span>
              {isTyping ? 'Typing...' : `${message.length} characters`}
            </span>
            <span>Press Enter to send, Shift+Enter for new line</span>
          </div>
        </div>
      </div>
    </div>
  )
}