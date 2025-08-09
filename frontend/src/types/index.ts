// User and Authentication types
export interface User {
  user_id: string
  email: string
  full_name: string
  role: 'employee' | 'manager' | 'admin'
  permissions: string[]
  is_active: boolean
}

export interface LoginRequest {
  email: string
  password: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user_info: User
}

// Chat and Conversation types
export interface ChatMessage {
  message_id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  llm_used?: string
  intent?: string
  metadata?: Record<string, any>
  timestamp: string
}

export interface ChatRequest {
  message: string
  session_id: string
  context?: Record<string, any>
}

export interface ChatResponse {
  response: string
  session_id: string
  message_id: string
  llm_used: string
  intent?: string
  suggested_actions?: string[]
  updated_plan?: OnboardingPlanSummary
}

// Onboarding types
export interface OnboardingPlanStep {
  step_id: string
  title: string
  description: string
  estimated_duration: string
  priority: 'low' | 'medium' | 'high'
  dependencies: string[]
  tools_needed: string[]
  status: 'pending' | 'in_progress' | 'completed' | 'blocked'
  progress?: number
  assigned_to?: string
  due_date?: string
  notes?: string
}

export interface OnboardingPlan {
  user_profile: {
    user_id: string
    full_name: string
    job_role: string
    department?: string
    start_date?: string
  }
  plan_steps: OnboardingPlanStep[]
  created_at: string
  estimated_completion: string
  progress_summary?: OnboardingPlanSummary
}

export interface OnboardingPlanSummary {
  total_tasks: number
  completed_tasks: number
  current_step?: string
  progress_percentage: number
}

// Approval types
export interface ApprovalRequest {
  request_id: string
  session_id: string
  action_type: string
  action_description: string
  action_details: Record<string, any>
  risk_level: 'low' | 'medium' | 'high'
  requester: string
  status: 'pending' | 'approved' | 'rejected' | 'expired'
  expires_at: string
  created_at: string
  approved_by?: string
  approved_at?: string
  approval_reason?: string
}

export interface ApprovalStats {
  total: number
  high_risk: number
  medium_risk: number
  low_risk: number
  escalated: number
  expiring_soon: number
}

// WebSocket types
export interface WebSocketMessage {
  category: 'system' | 'chat' | 'notification' | 'approval'
  type: string
  data: Record<string, any>
  session_id: string
  timestamp: string
  message_id: string
}

export interface NotificationMessage {
  type: 'chat_message' | 'task_update' | 'plan_updated' | 'tool_executed' | 'approval_request' | 'approval_response' | 'system_alert' | 'error_notification'
  data: Record<string, any>
  priority: 'low' | 'medium' | 'high' | 'critical'
  timestamp: string
  session_id: string
  id: string
}

// API Response types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

// File upload types
export interface FileUploadResponse {
  file_id: string
  filename: string
  file_size: number
  content_type: string
  upload_url?: string
}

// Progress and Status types
export interface ProgressStatus {
  current: number
  total: number
  percentage: number
  status: 'idle' | 'in_progress' | 'completed' | 'error'
  message?: string
}

// Voice integration types
export interface VoiceCall {
  call_id: string
  status: 'connecting' | 'connected' | 'in_progress' | 'ended' | 'failed'
  duration?: number
  transcript?: string
  session_id: string
  started_at: string
  ended_at?: string
}

// Tool execution types
export interface ToolExecution {
  tool_name: string
  action: string
  parameters: Record<string, any>
  success: boolean
  result: Record<string, any>
  execution_time: number
  error?: string
}

// Dashboard stats types
export interface DashboardStats {
  total_sessions: number
  active_sessions: number
  completed_tasks: number
  pending_approvals: number
  recent_activity: ActivityItem[]
}

export interface ActivityItem {
  id: string
  type: 'chat' | 'task' | 'approval' | 'tool'
  title: string
  description: string
  timestamp: string
  status: 'success' | 'pending' | 'error'
  user?: string
}

// Form types
export interface FormField {
  name: string
  label: string
  type: 'text' | 'email' | 'password' | 'textarea' | 'select' | 'checkbox' | 'file'
  placeholder?: string
  required?: boolean
  options?: { value: string; label: string }[]
  validation?: Record<string, any>
}

// Navigation types
export interface NavItem {
  name: string
  href: string
  icon: React.ComponentType<any>
  badge?: string | number
  requiredRole?: string[]
  requiredPermissions?: string[]
}

// Theme and UI types
export interface Theme {
  mode: 'light' | 'dark'
  primaryColor: string
  accentColor: string
}

export interface UIState {
  sidebarOpen: boolean
  theme: Theme
  notifications: NotificationMessage[]
  loading: boolean
}

// Settings types
export interface UserSettings {
  notifications: {
    email: boolean
    push: boolean
    chat: boolean
    approvals: boolean
  }
  preferences: {
    language: string
    timezone: string
    dateFormat: string
    theme: 'light' | 'dark' | 'auto'
  }
  privacy: {
    profileVisible: boolean
    activityTracking: boolean
  }
}

// Error types
export interface ApiError {
  message: string
  code?: string
  details?: Record<string, any>
  timestamp: string
}

export interface FormError {
  field: string
  message: string
}

// Utility types
export type LoadingState = 'idle' | 'loading' | 'success' | 'error'
export type SortDirection = 'asc' | 'desc'
export type FilterOption = { value: string; label: string; count?: number }

// Component prop types
export interface ComponentProps {
  className?: string
  children?: React.ReactNode
}

export interface ModalProps extends ComponentProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

export interface TableColumn<T = any> {
  key: keyof T
  label: string
  sortable?: boolean
  render?: (value: any, row: T) => React.ReactNode
  width?: string
}

export interface PaginationInfo {
  page: number
  limit: number
  total: number
  totalPages: number
}