import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { 
  UserCircleIcon,
  PencilIcon,
  KeyIcon,
  ShieldCheckIcon,
  CheckIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import { useAuth } from '@/contexts/AuthContext'
import { authApi } from '@/lib/api'
import toast from 'react-hot-toast'

interface PasswordChangeForm {
  current_password: string
  new_password: string
  confirm_password: string
}

export default function ProfilePage() {
  const { user, updateUser } = useAuth()
  const [isEditing, setIsEditing] = useState(false)
  const [showPasswordForm, setShowPasswordForm] = useState(false)

  const { register, handleSubmit, formState: { errors }, reset, watch } = useForm<PasswordChangeForm>()

  // Change password mutation
  const changePasswordMutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      authApi.changePassword(data),
    onSuccess: () => {
      toast.success('Password changed successfully')
      setShowPasswordForm(false)
      reset()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to change password')
    }
  })

  const newPassword = watch('new_password')

  const onSubmitPasswordChange = (data: PasswordChangeForm) => {
    if (data.new_password !== data.confirm_password) {
      toast.error('New passwords do not match')
      return
    }
    
    if (data.new_password.length < 6) {
      toast.error('New password must be at least 6 characters long')
      return
    }

    changePasswordMutation.mutate({
      current_password: data.current_password,
      new_password: data.new_password
    })
  }

  const getPermissionDescription = (permission: string) => {
    const descriptions: { [key: string]: string } = {
      '*': 'Full administrative access to all features',
      'onboarding:read': 'View onboarding plans and progress',
      'onboarding:write': 'Create and modify onboarding plans',
      'onboarding:approve': 'Approve onboarding plan changes',
      'chat:access': 'Access to chat with AI assistant',
      'approvals:manage': 'Manage approval requests and workflows',
      'users:view': 'View user information and profiles',
      'system:internal': 'Internal system operations'
    }
    return descriptions[permission] || permission
  }

  const getRoleDescription = (role: string) => {
    const descriptions: { [key: string]: string } = {
      'employee': 'Standard employee with basic access to onboarding features',
      'manager': 'Manager with approval permissions and team oversight',
      'admin': 'Administrator with full system access and management capabilities'
    }
    return descriptions[role] || role
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-danger-100 text-danger-800'
      case 'manager':
        return 'bg-warning-100 text-warning-800'
      default:
        return 'bg-primary-100 text-primary-800'
    }
  }

  if (!user) return null

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <div className="w-20 h-20 mx-auto mb-4 bg-primary-500 rounded-full flex items-center justify-center">
          <span className="text-white text-2xl font-bold">
            {user.full_name.charAt(0)}
          </span>
        </div>
        <h1 className="text-2xl font-bold text-secondary-900 mb-2">{user.full_name}</h1>
        <p className="text-secondary-600">{user.email}</p>
        <div className="flex items-center justify-center space-x-2 mt-2">
          <span className={`badge ${getRoleBadgeColor(user.role)}`}>
            {user.role}
          </span>
          {user.is_active && (
            <span className="badge bg-success-100 text-success-800">
              Active
            </span>
          )}
        </div>
      </div>

      {/* Profile Information */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <UserCircleIcon className="h-5 w-5 text-secondary-400" />
              <h2 className="text-lg font-semibold text-secondary-900">Profile Information</h2>
            </div>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="btn btn-ghost btn-sm"
            >
              <PencilIcon className="h-4 w-4 mr-1" />
              {isEditing ? 'Cancel' : 'Edit'}
            </button>
          </div>
        </div>
        <div className="card-content">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-secondary-700 mb-2">
                Full Name
              </label>
              {isEditing ? (
                <input
                  type="text"
                  defaultValue={user.full_name}
                  className="input"
                  placeholder="Enter your full name"
                />
              ) : (
                <p className="text-secondary-900">{user.full_name}</p>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium text-secondary-700 mb-2">
                Email Address
              </label>
              <p className="text-secondary-900">{user.email}</p>
              <p className="text-xs text-secondary-500 mt-1">
                Email cannot be changed
              </p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-secondary-700 mb-2">
                User ID
              </label>
              <p className="text-secondary-900 font-mono text-sm">{user.user_id}</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-secondary-700 mb-2">
                Account Status
              </label>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${user.is_active ? 'bg-success-500' : 'bg-danger-500'}`} />
                <span className={user.is_active ? 'text-success-600' : 'text-danger-600'}>
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>
          
          {isEditing && (
            <div className="flex items-center justify-end space-x-3 mt-6 pt-6 border-t border-secondary-200">
              <button
                onClick={() => setIsEditing(false)}
                className="btn btn-ghost"
              >
                Cancel
              </button>
              <button className="btn btn-primary">
                Save Changes
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Role & Permissions */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center space-x-2">
            <ShieldCheckIcon className="h-5 w-5 text-secondary-400" />
            <h2 className="text-lg font-semibold text-secondary-900">Role & Permissions</h2>
          </div>
        </div>
        <div className="card-content">
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-medium text-secondary-700 mb-2">Current Role</h3>
              <div className="flex items-center space-x-3">
                <span className={`badge ${getRoleBadgeColor(user.role)}`}>
                  {user.role}
                </span>
                <span className="text-sm text-secondary-600">
                  {getRoleDescription(user.role)}
                </span>
              </div>
            </div>
            
            <div>
              <h3 className="text-sm font-medium text-secondary-700 mb-3">Permissions</h3>
              <div className="space-y-3">
                {user.permissions.map((permission, index) => (
                  <div key={index} className="flex items-start space-x-3 p-3 bg-secondary-50 rounded-lg">
                    <CheckIcon className="h-5 w-5 text-success-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-secondary-900">{permission}</p>
                      <p className="text-xs text-secondary-600 mt-1">
                        {getPermissionDescription(permission)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            {user.permissions.includes('*') && (
              <div className="bg-warning-50 border border-warning-200 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <ShieldCheckIcon className="h-5 w-5 text-warning-600" />
                  <p className="text-sm font-medium text-warning-800">Administrator Access</p>
                </div>
                <p className="text-xs text-warning-700 mt-1">
                  You have full administrative access to all system features and functions.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Security Settings */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center space-x-2">
            <KeyIcon className="h-5 w-5 text-secondary-400" />
            <h2 className="text-lg font-semibold text-secondary-900">Security Settings</h2>
          </div>
        </div>
        <div className="card-content">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-secondary-900">Password</h3>
                <p className="text-sm text-secondary-600">
                  Change your password to keep your account secure
                </p>
              </div>
              <button
                onClick={() => setShowPasswordForm(!showPasswordForm)}
                className="btn btn-outline btn-sm"
              >
                {showPasswordForm ? 'Cancel' : 'Change Password'}
              </button>
            </div>
            
            {showPasswordForm && (
              <form onSubmit={handleSubmit(onSubmitPasswordChange)} className="space-y-4 p-4 bg-secondary-50 rounded-lg">
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Current Password
                  </label>
                  <input
                    {...register('current_password', { required: 'Current password is required' })}
                    type="password"
                    className={`input ${errors.current_password ? 'border-danger-300' : ''}`}
                    placeholder="Enter your current password"
                  />
                  {errors.current_password && (
                    <p className="mt-1 text-sm text-danger-600">{errors.current_password.message}</p>
                  )}
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    New Password
                  </label>
                  <input
                    {...register('new_password', { 
                      required: 'New password is required',
                      minLength: { value: 6, message: 'Password must be at least 6 characters' }
                    })}
                    type="password"
                    className={`input ${errors.new_password ? 'border-danger-300' : ''}`}
                    placeholder="Enter your new password"
                  />
                  {errors.new_password && (
                    <p className="mt-1 text-sm text-danger-600">{errors.new_password.message}</p>
                  )}
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-2">
                    Confirm New Password
                  </label>
                  <input
                    {...register('confirm_password', { 
                      required: 'Please confirm your new password',
                      validate: value => value === newPassword || 'Passwords do not match'
                    })}
                    type="password"
                    className={`input ${errors.confirm_password ? 'border-danger-300' : ''}`}
                    placeholder="Confirm your new password"
                  />
                  {errors.confirm_password && (
                    <p className="mt-1 text-sm text-danger-600">{errors.confirm_password.message}</p>
                  )}
                </div>
                
                <div className="flex items-center justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowPasswordForm(false)
                      reset()
                    }}
                    className="btn btn-ghost btn-sm"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={changePasswordMutation.isPending}
                    className="btn btn-primary btn-sm"
                  >
                    {changePasswordMutation.isPending ? 'Changing...' : 'Change Password'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>

      {/* Account Information */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-secondary-900">Account Information</h2>
        </div>
        <div className="card-content">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
            <div>
              <h3 className="font-medium text-secondary-700 mb-2">Account Created</h3>
              <p className="text-secondary-600">Information not available</p>
            </div>
            
            <div>
              <h3 className="font-medium text-secondary-700 mb-2">Last Login</h3>
              <p className="text-secondary-600">Information not available</p>
            </div>
            
            <div>
              <h3 className="font-medium text-secondary-700 mb-2">Sessions</h3>
              <p className="text-secondary-600">Current session active</p>
            </div>
            
            <div>
              <h3 className="font-medium text-secondary-700 mb-2">Two-Factor Authentication</h3>
              <div className="flex items-center space-x-2">
                <XMarkIcon className="h-4 w-4 text-danger-500" />
                <span className="text-danger-600">Not enabled</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}