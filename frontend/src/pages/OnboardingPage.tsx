import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { 
  ClipboardDocumentListIcon,
  DocumentArrowUpIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  PlayIcon,
  PauseIcon,
  ArrowDownTrayIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/react/24/outline'
import { useAuth } from '@/contexts/AuthContext'
import { onboardingApi } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import type { OnboardingPlan, OnboardingPlanStep } from '@/types'

export default function OnboardingPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [sessionId] = useState(() => `onboarding_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  const [dragActive, setDragActive] = useState(false)
  const [selectedTask, setSelectedTask] = useState<string | null>(null)

  // Load onboarding plan
  const { data: planData, isLoading: planLoading } = useQuery({
    queryKey: ['onboarding-plan', sessionId],
    queryFn: () => onboardingApi.getPlan(sessionId),
    retry: false,
  })

  // Load progress
  const { data: progressData } = useQuery({
    queryKey: ['onboarding-progress', sessionId],
    queryFn: () => onboardingApi.getProgress(sessionId),
  })

  // Upload resume mutation
  const uploadResumeMutation = useMutation({
    mutationFn: (file: File) => onboardingApi.uploadResume(file),
    onSuccess: async () => {
      toast.success('Resume uploaded successfully!')
      // Analyze resume after upload
      await analyzeResumeMutation.mutateAsync()
    },
    onError: () => {
      toast.error('Failed to upload resume')
    }
  })

  // Analyze resume mutation
  const analyzeResumeMutation = useMutation({
    mutationFn: () => onboardingApi.analyzeResume(sessionId),
    onSuccess: async () => {
      toast.success('Resume analyzed! Creating your onboarding plan...')
      // Create plan after analysis
      await createPlanMutation.mutateAsync()
    },
    onError: () => {
      toast.error('Failed to analyze resume')
    }
  })

  // Create plan mutation
  const createPlanMutation = useMutation({
    mutationFn: () => onboardingApi.createPlan(sessionId),
    onSuccess: () => {
      toast.success('Onboarding plan created!')
      queryClient.invalidateQueries({ queryKey: ['onboarding-plan', sessionId] })
      queryClient.invalidateQueries({ queryKey: ['onboarding-progress', sessionId] })
    },
    onError: () => {
      toast.error('Failed to create onboarding plan')
    }
  })

  // Update task status mutation
  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, status, notes }: { taskId: string, status: string, notes?: string }) =>
      onboardingApi.updateTaskStatus(sessionId, taskId, status, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding-plan', sessionId] })
      queryClient.invalidateQueries({ queryKey: ['onboarding-progress', sessionId] })
    }
  })

  // Execute tool mutation
  const executeToolMutation = useMutation({
    mutationFn: ({ toolName, action, parameters }: { toolName: string, action: string, parameters: any }) =>
      onboardingApi.executeTool(sessionId, toolName, action, parameters),
    onSuccess: (data) => {
      if (data.success) {
        toast.success(`Tool executed successfully: ${data.data.tool_name}`)
      } else {
        toast.error(`Tool execution failed: ${data.message}`)
      }
      queryClient.invalidateQueries({ queryKey: ['onboarding-plan', sessionId] })
    }
  })

  // Export plan mutation
  const exportPlanMutation = useMutation({
    mutationFn: (format: 'pdf' | 'json' | 'csv') => onboardingApi.exportPlan(sessionId, format),
    onSuccess: (blob, format) => {
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `onboarding-plan.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success(`Plan exported as ${format.toUpperCase()}`)
    }
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (file) {
      uploadResumeMutation.mutate(file)
    }
  }, [uploadResumeMutation])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt']
    },
    maxFiles: 1,
    multiple: false
  })

  const plan: OnboardingPlan | null = planData?.data || null
  const progress = progressData?.data?.progress_summary || null

  const getTaskStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-success-600 bg-success-50'
      case 'in_progress':
        return 'text-primary-600 bg-primary-50'
      case 'blocked':
        return 'text-danger-600 bg-danger-50'
      default:
        return 'text-secondary-600 bg-secondary-50'
    }
  }

  const getTaskStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return CheckCircleIcon
      case 'in_progress':
        return PlayIcon
      case 'blocked':
        return ExclamationCircleIcon
      default:
        return ClockIcon
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-danger-100 text-danger-800'
      case 'medium':
        return 'bg-warning-100 text-warning-800'
      default:
        return 'bg-secondary-100 text-secondary-800'
    }
  }

  const handleTaskAction = async (task: OnboardingPlanStep, action: string) => {
    switch (action) {
      case 'start':
        await updateTaskMutation.mutateAsync({
          taskId: task.step_id,
          status: 'in_progress'
        })
        toast.success('Task started!')
        break
      case 'complete':
        await updateTaskMutation.mutateAsync({
          taskId: task.step_id,
          status: 'completed'
        })
        toast.success('Task completed!')
        break
      case 'execute_tool':
        if (task.tools_needed.length > 0) {
          const toolName = task.tools_needed[0]
          await executeToolMutation.mutateAsync({
            toolName,
            action: 'execute',
            parameters: { task_id: task.step_id }
          })
        }
        break
    }
  }

  if (planLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 loading-spinner border-primary-600 mx-auto mb-4" />
          <p className="text-secondary-600">Loading your onboarding plan...</p>
        </div>
      </div>
    )
  }

  if (!plan) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <ClipboardDocumentListIcon className="h-12 w-12 text-secondary-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-secondary-900 mb-2">Welcome to Your Onboarding Journey</h1>
          <p className="text-secondary-600">
            Let's get started by uploading your resume to create a personalized onboarding plan.
          </p>
        </div>

        {/* Resume Upload */}
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-semibold text-secondary-900">Upload Your Resume</h2>
            <p className="text-sm text-secondary-600">
              Upload your resume to generate a customized onboarding plan based on your background and skills.
            </p>
          </div>
          <div className="card-content">
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragActive || dragActive
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-secondary-300 hover:border-secondary-400'
              }`}
            >
              <input {...getInputProps()} />
              <DocumentArrowUpIcon className="h-12 w-12 text-secondary-400 mx-auto mb-4" />
              <div className="space-y-2">
                <p className="text-lg font-medium text-secondary-900">
                  {isDragActive ? 'Drop your resume here' : 'Drag & drop your resume'}
                </p>
                <p className="text-sm text-secondary-500">
                  or <span className="text-primary-600 font-medium">click to browse</span>
                </p>
                <p className="text-xs text-secondary-400">
                  Supports PDF, DOC, DOCX, and TXT files
                </p>
              </div>
            </div>

            {(uploadResumeMutation.isPending || analyzeResumeMutation.isPending || createPlanMutation.isPending) && (
              <div className="mt-6 bg-primary-50 border border-primary-200 rounded-lg p-4">
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 loading-spinner border-primary-600" />
                  <div>
                    <p className="text-sm font-medium text-primary-900">
                      {uploadResumeMutation.isPending && 'Uploading resume...'}
                      {analyzeResumeMutation.isPending && 'Analyzing your background...'}
                      {createPlanMutation.isPending && 'Creating personalized plan...'}
                    </p>
                    <p className="text-xs text-primary-700">
                      This may take a few moments while I analyze your experience and skills.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900 mb-2">Your Onboarding Plan</h1>
          <p className="text-secondary-600">
            Welcome, {plan.user_profile.full_name}! Here's your personalized onboarding journey.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => exportPlanMutation.mutate('pdf')}
            className="btn btn-outline btn-sm"
            disabled={exportPlanMutation.isPending}
          >
            <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
            Export PDF
          </button>
        </div>
      </div>

      {/* Progress Overview */}
      {progress && (
        <div className="bg-gradient-to-r from-primary-50 to-primary-100 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-primary-900">Overall Progress</h3>
              <p className="text-primary-700">
                {progress.completed_tasks} of {progress.total_tasks} tasks completed
              </p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-primary-900">
                {Math.round(progress.progress_percentage)}%
              </p>
              <p className="text-sm text-primary-700">Complete</p>
            </div>
          </div>
          <div className="w-full bg-primary-200 rounded-full h-3">
            <div
              className="bg-primary-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${progress.progress_percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* User Profile */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-secondary-900">Profile Information</h3>
        </div>
        <div className="card-content">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-secondary-600">Name</p>
              <p className="text-secondary-900">{plan.user_profile.full_name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-secondary-600">Role</p>
              <p className="text-secondary-900">{plan.user_profile.job_role}</p>
            </div>
            {plan.user_profile.department && (
              <div>
                <p className="text-sm font-medium text-secondary-600">Department</p>
                <p className="text-secondary-900">{plan.user_profile.department}</p>
              </div>
            )}
            {plan.user_profile.start_date && (
              <div>
                <p className="text-sm font-medium text-secondary-600">Start Date</p>
                <p className="text-secondary-900">
                  {new Date(plan.user_profile.start_date).toLocaleDateString()}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tasks */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-secondary-900">Onboarding Tasks</h3>
          <p className="text-sm text-secondary-600">
            Complete these tasks to finish your onboarding process
          </p>
        </div>
        <div className="card-content">
          <div className="space-y-4">
            {plan.plan_steps.map((task, index) => {
              const StatusIcon = getTaskStatusIcon(task.status)
              const canStart = task.status === 'pending' && (
                task.dependencies.length === 0 ||
                task.dependencies.every(depId => 
                  plan.plan_steps.find(t => t.step_id === depId)?.status === 'completed'
                )
              )

              return (
                <div
                  key={task.step_id}
                  className={`border rounded-lg p-4 transition-all ${
                    selectedTask === task.step_id ? 'border-primary-300 shadow-md' : 'border-secondary-200'
                  }`}
                >
                  <div className="flex items-start space-x-4">
                    <div className="flex-shrink-0">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${getTaskStatusColor(task.status)}`}>
                        <StatusIcon className="h-4 w-4" />
                      </div>
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-medium text-secondary-900">{task.title}</h4>
                        <div className="flex items-center space-x-2">
                          <span className={`badge ${getPriorityColor(task.priority)}`}>
                            {task.priority}
                          </span>
                          <span className={`badge ${getTaskStatusColor(task.status)}`}>
                            {task.status.replace('_', ' ')}
                          </span>
                        </div>
                      </div>
                      
                      <p className="text-sm text-secondary-600 mb-3">{task.description}</p>
                      
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4 text-xs text-secondary-500">
                          <span>📅 {task.estimated_duration}</span>
                          {task.tools_needed.length > 0 && (
                            <span>🔧 {task.tools_needed.join(', ')}</span>
                          )}
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          {task.status === 'pending' && canStart && (
                            <button
                              onClick={() => handleTaskAction(task, 'start')}
                              className="btn btn-primary btn-sm"
                              disabled={updateTaskMutation.isPending}
                            >
                              <PlayIcon className="h-3 w-3 mr-1" />
                              Start
                            </button>
                          )}
                          
                          {task.status === 'in_progress' && (
                            <button
                              onClick={() => handleTaskAction(task, 'complete')}
                              className="btn btn-success btn-sm"
                              disabled={updateTaskMutation.isPending}
                            >
                              <CheckCircleIcon className="h-3 w-3 mr-1" />
                              Complete
                            </button>
                          )}
                          
                          {task.tools_needed.length > 0 && task.status !== 'completed' && (
                            <button
                              onClick={() => handleTaskAction(task, 'execute_tool')}
                              className="btn btn-outline btn-sm"
                              disabled={executeToolMutation.isPending}
                            >
                              Execute Tool
                            </button>
                          )}

                          <button
                            onClick={() => setSelectedTask(selectedTask === task.step_id ? null : task.step_id)}
                            className="btn btn-ghost btn-sm"
                          >
                            {selectedTask === task.step_id ? 'Less' : 'More'}
                          </button>
                        </div>
                      </div>
                      
                      {selectedTask === task.step_id && (
                        <div className="mt-4 pt-4 border-t border-secondary-200">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                            <div>
                              <p className="font-medium text-secondary-700 mb-1">Dependencies:</p>
                              <p className="text-secondary-600">
                                {task.dependencies.length > 0 ? task.dependencies.join(', ') : 'None'}
                              </p>
                            </div>
                            <div>
                              <p className="font-medium text-secondary-700 mb-1">Tools Needed:</p>
                              <p className="text-secondary-600">
                                {task.tools_needed.length > 0 ? task.tools_needed.join(', ') : 'None'}
                              </p>
                            </div>
                            {task.notes && (
                              <div className="md:col-span-2">
                                <p className="font-medium text-secondary-700 mb-1">Notes:</p>
                                <p className="text-secondary-600">{task.notes}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Need Help */}
      <div className="bg-secondary-50 rounded-lg p-6">
        <div className="flex items-center space-x-3">
          <ChatBubbleLeftRightIcon className="h-8 w-8 text-secondary-400" />
          <div>
            <h3 className="text-lg font-medium text-secondary-900">Need Help?</h3>
            <p className="text-secondary-600">
              Stuck on a task or have questions? Chat with me for personalized assistance.
            </p>
          </div>
          <div className="flex-shrink-0">
            <a href="/chat" className="btn btn-primary">
              Chat Now
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}