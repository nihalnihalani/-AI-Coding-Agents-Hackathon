import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'
import { useAuth } from '@/contexts/AuthContext'
import type { LoginRequest } from '@/types'

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false)
  const [showDemoUsers, setShowDemoUsers] = useState(false)
  const { login } = useAuth()

  const { register, handleSubmit, formState: { errors, isSubmitting }, setValue } = useForm<LoginRequest>()

  const onSubmit = async (data: LoginRequest) => {
    try {
      await login(data)
    } catch (error) {
      // Error handling is done in the login function
    }
  }

  const demoUsers = [
    { email: 'demo@aura.ai', password: 'demo123', role: 'Employee', description: 'Standard employee account' },
    { email: 'manager@aura.ai', password: 'manager123', role: 'Manager', description: 'Manager with approval permissions' },
    { email: 'admin@aura.ai', password: 'admin123', role: 'Admin', description: 'Full admin access' },
  ]

  const fillDemoCredentials = (email: string, password: string) => {
    setValue('email', email)
    setValue('password', password)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-secondary-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center shadow-lg">
            <span className="text-white font-bold text-2xl">A</span>
          </div>
          <h2 className="text-3xl font-bold text-secondary-900 mb-2">Welcome to Aura</h2>
          <p className="text-secondary-600">Your AI-powered onboarding assistant</p>
        </div>

        {/* Login Form */}
        <div className="bg-white shadow-xl rounded-lg p-8">
          <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-secondary-700 mb-2">
                Email address
              </label>
              <input
                {...register('email', { 
                  required: 'Email is required',
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: 'Invalid email address'
                  }
                })}
                type="email"
                autoComplete="email"
                className={`input ${errors.email ? 'border-danger-300 focus:ring-danger-500' : ''}`}
                placeholder="you@company.com"
              />
              {errors.email && (
                <p className="mt-1 text-sm text-danger-600">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-secondary-700 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  {...register('password', { required: 'Password is required' })}
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  className={`input pr-10 ${errors.password ? 'border-danger-300 focus:ring-danger-500' : ''}`}
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeSlashIcon className="h-5 w-5 text-secondary-400" />
                  ) : (
                    <EyeIcon className="h-5 w-5 text-secondary-400" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-sm text-danger-600">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full btn btn-primary btn-lg relative"
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 loading-spinner border-white mr-2" />
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          {/* Demo Users Section */}
          <div className="mt-6 pt-6 border-t border-secondary-200">
            <button
              type="button"
              onClick={() => setShowDemoUsers(!showDemoUsers)}
              className="w-full text-sm text-secondary-600 hover:text-secondary-900 flex items-center justify-center"
            >
              {showDemoUsers ? 'Hide' : 'Show'} demo accounts
              <svg
                className={`ml-2 h-4 w-4 transform transition-transform ${showDemoUsers ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {showDemoUsers && (
              <div className="mt-4 space-y-3">
                <p className="text-xs text-secondary-500 text-center">
                  Click any demo account to fill the login form
                </p>
                {demoUsers.map((user, index) => (
                  <div
                    key={index}
                    className="p-3 bg-secondary-50 rounded-lg cursor-pointer hover:bg-secondary-100 transition-colors"
                    onClick={() => fillDemoCredentials(user.email, user.password)}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-secondary-900">{user.role}</p>
                        <p className="text-xs text-secondary-600">{user.email}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-secondary-500">{user.description}</p>
                      </div>
                    </div>
                  </div>
                ))}
                <p className="text-xs text-warning-600 text-center">
                  ⚠️ Demo accounts are for testing purposes only
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="text-center">
          <p className="text-sm text-secondary-500">
            Powered by Aura AI • Built with Claude & Gemini
          </p>
        </div>
      </div>
    </div>
  )
}