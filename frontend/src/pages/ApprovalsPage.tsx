import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  FunnelIcon,
  CheckIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import { useAuth } from '@/contexts/AuthContext'
import { approvalsApi } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import type { ApprovalRequest } from '@/types'

export default function ApprovalsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  
  const [selectedTab, setSelectedTab] = useState<'pending' | 'history'>('pending')
  const [riskFilter, setRiskFilter] = useState<string>('')
  const [selectedRequests, setSelectedRequests] = useState<string[]>([])
  const [showApprovalModal, setShowApprovalModal] = useState<string | null>(null)
  const [approvalReason, setApprovalReason] = useState('')
  const [rejectionReason, setRejectionReason] = useState('')

  // Load pending approvals
  const { data: pendingData, isLoading: pendingLoading } = useQuery({
    queryKey: ['pending-approvals', riskFilter],
    queryFn: () => approvalsApi.getPendingApprovals(undefined, riskFilter || undefined),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Load approval history
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['approval-history'],
    queryFn: () => approvalsApi.getApprovalHistory(50),
    enabled: selectedTab === 'history',
  })

  // Load dashboard stats
  const { data: dashboardData } = useQuery({
    queryKey: ['approvals-dashboard'],
    queryFn: () => approvalsApi.getDashboard(),
    refetchInterval: 60000, // Refresh every minute
  })

  // Approve request mutation
  const approveMutation = useMutation({
    mutationFn: ({ requestId, reason }: { requestId: string, reason?: string }) =>
      approvalsApi.approveRequest(requestId, {
        approver_id: user?.user_id || '',
        approval_reason: reason,
      }),
    onSuccess: () => {
      toast.success('Request approved successfully')
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] })
      queryClient.invalidateQueries({ queryKey: ['approval-history'] })
      queryClient.invalidateQueries({ queryKey: ['approvals-dashboard'] })
      setShowApprovalModal(null)
      setApprovalReason('')
    },
    onError: () => {
      toast.error('Failed to approve request')
    }
  })

  // Reject request mutation
  const rejectMutation = useMutation({
    mutationFn: ({ requestId, reason }: { requestId: string, reason: string }) =>
      approvalsApi.rejectRequest(requestId, {
        approver_id: user?.user_id || '',
        rejection_reason: reason,
      }),
    onSuccess: () => {
      toast.success('Request rejected')
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] })
      queryClient.invalidateQueries({ queryKey: ['approval-history'] })
      queryClient.invalidateQueries({ queryKey: ['approvals-dashboard'] })
      setShowApprovalModal(null)
      setRejectionReason('')
    },
    onError: () => {
      toast.error('Failed to reject request')
    }
  })

  // Bulk approve mutation
  const bulkApproveMutation = useMutation({
    mutationFn: (requestIds: string[]) =>
      approvalsApi.bulkApprove(requestIds, user?.user_id || '', 'Bulk approval'),
    onSuccess: (data) => {
      const successCount = data.data.summary.successful_approvals
      toast.success(`${successCount} requests approved successfully`)
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] })
      queryClient.invalidateQueries({ queryKey: ['approvals-dashboard'] })
      setSelectedRequests([])
    },
    onError: () => {
      toast.error('Failed to bulk approve requests')
    }
  })

  const pendingApprovals: ApprovalRequest[] = pendingData?.data?.approvals || []
  const approvalHistory: ApprovalRequest[] = historyData?.data?.approvals || []
  const stats = dashboardData?.data || {}

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'high':
        return 'bg-danger-100 text-danger-800 border-danger-200'
      case 'medium':
        return 'bg-warning-100 text-warning-800 border-warning-200'
      default:
        return 'bg-success-100 text-success-800 border-success-200'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-success-100 text-success-800'
      case 'rejected':
        return 'bg-danger-100 text-danger-800'
      case 'expired':
        return 'bg-secondary-100 text-secondary-800'
      default:
        return 'bg-warning-100 text-warning-800'
    }
  }

  const handleBulkApprove = () => {
    if (selectedRequests.length === 0) {
      toast.error('Please select requests to approve')
      return
    }
    bulkApproveMutation.mutate(selectedRequests)
  }

  const handleRequestSelect = (requestId: string) => {
    setSelectedRequests(prev =>
      prev.includes(requestId)
        ? prev.filter(id => id !== requestId)
        : [...prev, requestId]
    )
  }

  const handleSelectAll = () => {
    if (selectedRequests.length === pendingApprovals.length) {
      setSelectedRequests([])
    } else {
      setSelectedRequests(pendingApprovals.map(req => req.request_id))
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Approval Management</h1>
          <p className="text-secondary-600">Review and manage approval requests</p>
        </div>
      </div>

      {/* Stats Cards */}
      {stats.pending_approvals && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg shadow-sm border border-secondary-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-secondary-600">Total Pending</p>
                <p className="text-2xl font-bold text-secondary-900">{stats.pending_approvals.total}</p>
              </div>
              <ClockIcon className="h-8 w-8 text-secondary-400" />
            </div>
          </div>
          
          <div className="bg-white p-4 rounded-lg shadow-sm border border-secondary-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-secondary-600">High Risk</p>
                <p className="text-2xl font-bold text-danger-600">{stats.pending_approvals.high_risk}</p>
              </div>
              <ExclamationTriangleIcon className="h-8 w-8 text-danger-400" />
            </div>
          </div>
          
          <div className="bg-white p-4 rounded-lg shadow-sm border border-secondary-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-secondary-600">Escalated</p>
                <p className="text-2xl font-bold text-warning-600">{stats.pending_approvals.escalated}</p>
              </div>
              <ExclamationTriangleIcon className="h-8 w-8 text-warning-400" />
            </div>
          </div>
          
          <div className="bg-white p-4 rounded-lg shadow-sm border border-secondary-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-secondary-600">Approval Rate</p>
                <p className="text-2xl font-bold text-success-600">
                  {stats.historical_stats ? Math.round(stats.historical_stats.approval_rate) : 0}%
                </p>
              </div>
              <CheckCircleIcon className="h-8 w-8 text-success-400" />
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-secondary-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setSelectedTab('pending')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              selectedTab === 'pending'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-secondary-500 hover:text-secondary-700 hover:border-secondary-300'
            }`}
          >
            Pending Approvals ({pendingApprovals.length})
          </button>
          <button
            onClick={() => setSelectedTab('history')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              selectedTab === 'history'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-secondary-500 hover:text-secondary-700 hover:border-secondary-300'
            }`}
          >
            History
          </button>
        </nav>
      </div>

      {/* Filters and Actions */}
      {selectedTab === 'pending' && (
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <FunnelIcon className="h-5 w-5 text-secondary-400" />
              <select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value)}
                className="input text-sm"
              >
                <option value="">All Risk Levels</option>
                <option value="high">High Risk</option>
                <option value="medium">Medium Risk</option>
                <option value="low">Low Risk</option>
              </select>
            </div>
            
            {pendingApprovals.length > 0 && (
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={selectedRequests.length === pendingApprovals.length}
                  onChange={handleSelectAll}
                  className="rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-secondary-600">
                  Select All ({selectedRequests.length})
                </span>
              </div>
            )}
          </div>
          
          {selectedRequests.length > 0 && (
            <button
              onClick={handleBulkApprove}
              disabled={bulkApproveMutation.isPending}
              className="btn btn-primary btn-sm"
            >
              {bulkApproveMutation.isPending ? 'Approving...' : `Approve Selected (${selectedRequests.length})`}
            </button>
          )}
        </div>
      )}

      {/* Content */}
      <div className="bg-white rounded-lg shadow-sm border border-secondary-200">
        {selectedTab === 'pending' ? (
          <div>
            {pendingLoading ? (
              <div className="p-8 text-center">
                <div className="w-8 h-8 loading-spinner border-primary-600 mx-auto mb-4" />
                <p className="text-secondary-600">Loading pending approvals...</p>
              </div>
            ) : pendingApprovals.length === 0 ? (
              <div className="p-8 text-center">
                <CheckCircleIcon className="h-12 w-12 text-secondary-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-secondary-900 mb-2">No Pending Approvals</h3>
                <p className="text-secondary-600">All caught up! No requests waiting for approval.</p>
              </div>
            ) : (
              <div className="divide-y divide-secondary-200">
                {pendingApprovals.map((request) => (
                  <div key={request.request_id} className="p-6 hover:bg-secondary-50">
                    <div className="flex items-start space-x-4">
                      <input
                        type="checkbox"
                        checked={selectedRequests.includes(request.request_id)}
                        onChange={() => handleRequestSelect(request.request_id)}
                        className="mt-1 rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                      />
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="text-lg font-medium text-secondary-900">
                            {request.action_description}
                          </h3>
                          <div className="flex items-center space-x-2">
                            <span className={`badge border ${getRiskColor(request.risk_level)}`}>
                              {request.risk_level} risk
                            </span>
                            <span className="text-xs text-secondary-500">
                              {formatDistanceToNow(new Date(request.created_at), { addSuffix: true })}
                            </span>
                          </div>
                        </div>
                        
                        <p className="text-sm text-secondary-600 mb-3">
                          <span className="font-medium">Type:</span> {request.action_type}
                        </p>
                        
                        <p className="text-sm text-secondary-600 mb-3">
                          <span className="font-medium">Requested by:</span> {request.requester}
                        </p>
                        
                        {request.expires_at && (
                          <p className="text-sm text-secondary-600 mb-4">
                            <span className="font-medium">Expires:</span> {' '}
                            {formatDistanceToNow(new Date(request.expires_at), { addSuffix: true })}
                          </p>
                        )}
                        
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => approveMutation.mutate({ requestId: request.request_id })}
                            disabled={approveMutation.isPending}
                            className="btn btn-success btn-sm"
                          >
                            <CheckIcon className="h-4 w-4 mr-1" />
                            Approve
                          </button>
                          
                          <button
                            onClick={() => setShowApprovalModal(request.request_id)}
                            className="btn btn-danger btn-sm"
                          >
                            <XMarkIcon className="h-4 w-4 mr-1" />
                            Reject
                          </button>
                          
                          <button className="btn btn-ghost btn-sm">
                            View Details
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div>
            {historyLoading ? (
              <div className="p-8 text-center">
                <div className="w-8 h-8 loading-spinner border-primary-600 mx-auto mb-4" />
                <p className="text-secondary-600">Loading approval history...</p>
              </div>
            ) : approvalHistory.length === 0 ? (
              <div className="p-8 text-center">
                <ClockIcon className="h-12 w-12 text-secondary-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-secondary-900 mb-2">No History</h3>
                <p className="text-secondary-600">No approval history found.</p>
              </div>
            ) : (
              <div className="divide-y divide-secondary-200">
                {approvalHistory.map((request) => (
                  <div key={request.request_id} className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-sm font-medium text-secondary-900">
                            {request.action_description}
                          </h3>
                          <span className={`badge ${getStatusColor(request.status)}`}>
                            {request.status}
                          </span>
                          <span className={`badge border ${getRiskColor(request.risk_level)}`}>
                            {request.risk_level} risk
                          </span>
                        </div>
                        
                        <div className="text-xs text-secondary-500 space-y-1">
                          <p>Requested by: {request.requester}</p>
                          <p>
                            {request.status === 'approved' ? 'Approved' : 'Rejected'} by: {request.approved_by}
                          </p>
                          <p>
                            {request.status === 'approved' ? 'Approved' : 'Rejected'} at: {' '}
                            {formatDistanceToNow(new Date(request.approved_at!), { addSuffix: true })}
                          </p>
                          {request.approval_reason && (
                            <p>Reason: {request.approval_reason}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Rejection Modal */}
      {showApprovalModal && (
        <div className="fixed inset-0 bg-secondary-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-medium text-secondary-900 mb-4">Reject Request</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-2">
                  Rejection Reason *
                </label>
                <textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Please provide a reason for rejection..."
                  className="w-full input"
                  rows={3}
                  required
                />
              </div>
              
              <div className="flex items-center justify-end space-x-3">
                <button
                  onClick={() => {
                    setShowApprovalModal(null)
                    setRejectionReason('')
                  }}
                  className="btn btn-ghost"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    if (rejectionReason.trim()) {
                      rejectMutation.mutate({
                        requestId: showApprovalModal,
                        reason: rejectionReason.trim()
                      })
                    } else {
                      toast.error('Please provide a rejection reason')
                    }
                  }}
                  disabled={rejectMutation.isPending || !rejectionReason.trim()}
                  className="btn btn-danger"
                >
                  {rejectMutation.isPending ? 'Rejecting...' : 'Reject Request'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}