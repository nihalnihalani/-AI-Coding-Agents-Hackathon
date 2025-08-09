import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  ChatBubbleLeftRightIcon,
  ClipboardDocumentListIcon,
  CheckCircleIcon,
  ClockIcon,
  UserGroupIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  BoltIcon
} from '@heroicons/react/24/outline'
import { useAuth } from '@/contexts/AuthContext'
import { useWebSocket } from '@/contexts/WebSocketContext'
import { dashboardApi, onboardingApi, approvalsApi } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'
import { Link } from 'react-router-dom'

export default function DashboardPage() {
  const { user } = useAuth()
  const { isConnected, notifications } = useWebSocket()
  const [sessionId] = useState(() => `dashboard_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)

  // Dashboard stats query
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardApi.getStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Onboarding progress query
  const { data: progressData } = useQuery({
    queryKey: ['onboarding-progress', sessionId],
    queryFn: () => onboardingApi.getProgress(sessionId),
    enabled: !!sessionId,
  })

  // Approvals dashboard (for managers)
  const { data: approvalsData } = useQuery({
    queryKey: ['approvals-dashboard'],
    queryFn: () => approvalsApi.getDashboard(),
    enabled: user?.role === 'manager' || user?.role === 'admin',
  })

  const recentNotifications = notifications.slice(0, 5)
  const progress = progressData?.data?.progress_summary || null

  const quickActions = [
    {
      name: 'Start Chat',
      description: 'Chat with Aura for help',
      href: '/chat',
      icon: ChatBubbleLeftRightIcon,
      color: 'bg-primary-500',
    },
    {
      name: 'View Onboarding',
      description: 'Check your progress',
      href: '/onboarding',
      icon: ClipboardDocumentListIcon,
      color: 'bg-success-500',
    },
    ...(user?.role === 'manager' || user?.role === 'admin' ? [{
      name: 'Manage Approvals',
      description: 'Review pending requests',
      href: '/approvals',
      icon: CheckCircleIcon,
      color: 'bg-warning-500',
    }] : []),
  ]

  const statsCards = [
    {
      name: 'Active Sessions',
      value: statsData?.active_sessions || 0,
      change: '+4.75%',
      changeType: 'positive' as const,
      icon: UserGroupIcon,
    },
    {
      name: 'Completed Tasks',
      value: progress?.completed_tasks || 0,
      total: progress?.total_tasks || 0,
      progress: progress?.progress_percentage || 0,
      icon: CheckCircleIcon,
    },
    {
      name: 'Pending Approvals',
      value: approvalsData?.data?.pending_approvals?.total || 0,
      change: approvalsData?.data?.pending_approvals?.high_risk > 0 ? `${approvalsData.data.pending_approvals.high_risk} high priority` : undefined,
      changeType: approvalsData?.data?.pending_approvals?.high_risk > 0 ? 'negative' as const : 'neutral' as const,
      icon: ExclamationTriangleIcon,
    },
    {
      name: 'Chat Messages',
      value: statsData?.total_messages || 0,
      change: '+12.5%',
      changeType: 'positive' as const,
      icon: ChatBubbleLeftRightIcon,
    },
  ]

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-800 rounded-lg shadow-sm p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">
              Welcome back, {user?.full_name?.split(' ')[0] || 'User'}! 👋
            </h1>
            <p className="text-primary-100 mb-4">
              Ready to continue your onboarding journey? I'm here to help you every step of the way.
            </p>
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success-400' : 'bg-danger-400'}`} />
                <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
              </div>
              <div className="flex items-center space-x-2">
                <BoltIcon className="h-4 w-4" />
                <span>Role: {user?.role}</span>
              </div>
            </div>
          </div>
          <div className="hidden sm:block">
            <div className="w-24 h-24 bg-white/10 rounded-full flex items-center justify-center">
              <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
                <span className="text-2xl font-bold">A</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold text-secondary-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {quickActions.map((action) => (
            <Link
              key={action.name}
              to={action.href}
              className="group relative bg-white p-6 rounded-lg shadow-sm border border-secondary-200 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${action.color}`}>
                  <action.icon className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-secondary-900 group-hover:text-primary-600">
                    {action.name}
                  </h3>
                  <p className="text-sm text-secondary-500">{action.description}</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Stats Grid */}
      <div>
        <h2 className="text-lg font-semibold text-secondary-900 mb-4">Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {statsCards.map((stat) => (
            <div key={stat.name} className="bg-white p-6 rounded-lg shadow-sm border border-secondary-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-secondary-600">{stat.name}</p>
                  <div className="flex items-baseline space-x-2">
                    <p className="text-2xl font-semibold text-secondary-900">
                      {stat.value}
                      {stat.total && <span className="text-lg text-secondary-500">/{stat.total}</span>}
                    </p>
                  </div>
                  {stat.progress !== undefined && (
                    <div className="mt-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-secondary-600">Progress</span>
                        <span className="font-medium">{Math.round(stat.progress)}%</span>
                      </div>
                      <div className="mt-1 w-full bg-secondary-200 rounded-full h-2">
                        <div
                          className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${stat.progress}%` }}
                        />
                      </div>
                    </div>
                  )}
                  {stat.change && (
                    <p className={`text-sm ${
                      stat.changeType === 'positive' ? 'text-success-600' :
                      stat.changeType === 'negative' ? 'text-danger-600' :
                      'text-secondary-600'
                    }`}>
                      {stat.change}
                    </p>
                  )}
                </div>
                <div className="p-2 bg-secondary-50 rounded-lg">
                  <stat.icon className="h-6 w-6 text-secondary-600" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Activity & Notifications */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Notifications */}
        <div className="bg-white rounded-lg shadow-sm border border-secondary-200">
          <div className="p-6 border-b border-secondary-200">
            <h3 className="text-lg font-medium text-secondary-900">Recent Activity</h3>
          </div>
          <div className="p-6">
            {recentNotifications.length === 0 ? (
              <div className="text-center py-8">
                <ClockIcon className="h-12 w-12 text-secondary-300 mx-auto mb-4" />
                <p className="text-sm text-secondary-500">No recent activity</p>
              </div>
            ) : (
              <div className="space-y-4">
                {recentNotifications.map((notification) => (
                  <div key={notification.id} className="flex space-x-3">
                    <div className={`flex-shrink-0 w-2 h-2 mt-2 rounded-full ${
                      notification.priority === 'critical' ? 'bg-danger-400' :
                      notification.priority === 'high' ? 'bg-warning-400' :
                      notification.priority === 'medium' ? 'bg-primary-400' :
                      'bg-secondary-400'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-secondary-900">
                        {notification.data.message || notification.type.replace('_', ' ')}
                      </p>
                      <p className="text-xs text-secondary-500">
                        {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Onboarding Progress */}
        <div className="bg-white rounded-lg shadow-sm border border-secondary-200">
          <div className="p-6 border-b border-secondary-200">
            <h3 className="text-lg font-medium text-secondary-900">Onboarding Progress</h3>
          </div>
          <div className="p-6">
            {progress ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-secondary-700">Overall Progress</span>
                  <span className="text-sm text-secondary-500">
                    {progress.completed_tasks} of {progress.total_tasks} tasks
                  </span>
                </div>
                <div className="w-full bg-secondary-200 rounded-full h-3">
                  <div
                    className="bg-gradient-to-r from-primary-500 to-primary-600 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${progress.progress_percentage}%` }}
                  />
                </div>
                <p className="text-2xl font-bold text-secondary-900">
                  {Math.round(progress.progress_percentage)}% Complete
                </p>
                {progress.current_step && (
                  <div className="mt-4 p-3 bg-primary-50 rounded-lg">
                    <p className="text-sm font-medium text-primary-900">Current Task:</p>
                    <p className="text-sm text-primary-700">{progress.current_step}</p>
                  </div>
                )}
                <div className="pt-4">
                  <Link
                    to="/onboarding"
                    className="btn btn-primary btn-sm w-full"
                  >
                    View Full Plan
                  </Link>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <ClipboardDocumentListIcon className="h-12 w-12 text-secondary-300 mx-auto mb-4" />
                <p className="text-sm text-secondary-500 mb-4">
                  No onboarding plan found
                </p>
                <Link
                  to="/onboarding"
                  className="btn btn-primary btn-sm"
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Manager Dashboard */}
      {(user?.role === 'manager' || user?.role === 'admin') && approvalsData && (
        <div className="bg-white rounded-lg shadow-sm border border-secondary-200">
          <div className="p-6 border-b border-secondary-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-secondary-900">Approvals Dashboard</h3>
              <Link
                to="/approvals"
                className="btn btn-outline btn-sm"
              >
                View All
              </Link>
            </div>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-secondary-900">
                  {approvalsData.data.pending_approvals?.total || 0}
                </p>
                <p className="text-sm text-secondary-600">Total Pending</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-warning-600">
                  {approvalsData.data.pending_approvals?.high_risk || 0}
                </p>
                <p className="text-sm text-secondary-600">High Risk</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-danger-600">
                  {approvalsData.data.pending_approvals?.escalated || 0}
                </p>
                <p className="text-sm text-secondary-600">Escalated</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}