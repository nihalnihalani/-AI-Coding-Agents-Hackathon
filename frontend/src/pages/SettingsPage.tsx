import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Cog6ToothIcon,
  BellIcon,
  GlobeAltIcon,
  EyeIcon,
  ShieldCheckIcon,
  ComputerDesktopIcon,
  MoonIcon,
  SunIcon,
  CheckIcon
} from '@heroicons/react/24/outline'
import { useAuth } from '@/contexts/AuthContext'
import { useWebSocket } from '@/contexts/WebSocketContext'
import { settingsApi } from '@/lib/api'
import toast from 'react-hot-toast'
import type { UserSettings } from '@/types'

export default function SettingsPage() {
  const { user } = useAuth()
  const { isConnected, subscribe } = useWebSocket()
  const queryClient = useQueryClient()
  
  const [selectedSection, setSelectedSection] = useState('notifications')

  // Load user settings
  const { data: settings, isLoading } = useQuery({
    queryKey: ['user-settings'],
    queryFn: () => settingsApi.getUserSettings(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Update settings mutation
  const updateSettingsMutation = useMutation({
    mutationFn: (updates: Partial<UserSettings>) => settingsApi.updateUserSettings(updates),
    onSuccess: () => {
      toast.success('Settings updated successfully')
      queryClient.invalidateQueries({ queryKey: ['user-settings'] })
    },
    onError: () => {
      toast.error('Failed to update settings')
    }
  })

  const currentSettings: UserSettings = settings || {
    notifications: {
      email: true,
      push: true,
      chat: true,
      approvals: true,
    },
    preferences: {
      language: 'en',
      timezone: 'UTC',
      dateFormat: 'MM/dd/yyyy',
      theme: 'light',
    },
    privacy: {
      profileVisible: true,
      activityTracking: true,
    },
  }

  const handleNotificationChange = (key: keyof UserSettings['notifications'], value: boolean) => {
    const updatedSettings = {
      ...currentSettings,
      notifications: {
        ...currentSettings.notifications,
        [key]: value,
      },
    }
    updateSettingsMutation.mutate(updatedSettings)

    // Update WebSocket subscriptions based on settings
    if (isConnected) {
      const types = []
      if (updatedSettings.notifications.chat) types.push('chat_message')
      if (updatedSettings.notifications.approvals) types.push('approval_request', 'approval_response')
      subscribe(types)
    }
  }

  const handlePreferenceChange = (key: keyof UserSettings['preferences'], value: string) => {
    const updatedSettings = {
      ...currentSettings,
      preferences: {
        ...currentSettings.preferences,
        [key]: value,
      },
    }
    updateSettingsMutation.mutate(updatedSettings)
  }

  const handlePrivacyChange = (key: keyof UserSettings['privacy'], value: boolean) => {
    const updatedSettings = {
      ...currentSettings,
      privacy: {
        ...currentSettings.privacy,
        [key]: value,
      },
    }
    updateSettingsMutation.mutate(updatedSettings)
  }

  const sections = [
    { id: 'notifications', name: 'Notifications', icon: BellIcon },
    { id: 'preferences', name: 'Preferences', icon: Cog6ToothIcon },
    { id: 'privacy', name: 'Privacy', icon: ShieldCheckIcon },
    { id: 'appearance', name: 'Appearance', icon: ComputerDesktopIcon },
    { id: 'language', name: 'Language & Region', icon: GlobeAltIcon },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 loading-spinner border-primary-600 mx-auto mb-4" />
          <p className="text-secondary-600">Loading settings...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center space-x-3 mb-8">
        <Cog6ToothIcon className="h-8 w-8 text-secondary-400" />
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Settings</h1>
          <p className="text-secondary-600">Manage your account preferences and settings</p>
        </div>
      </div>

      <div className="lg:grid lg:grid-cols-12 lg:gap-x-8">
        {/* Settings Navigation */}
        <aside className="lg:col-span-3">
          <nav className="space-y-1">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => setSelectedSection(section.id)}
                className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                  selectedSection === section.id
                    ? 'bg-primary-100 text-primary-900 border-r-2 border-primary-500'
                    : 'text-secondary-600 hover:bg-secondary-50 hover:text-secondary-900'
                }`}
              >
                <section.icon className="mr-3 h-5 w-5 flex-shrink-0" />
                {section.name}
              </button>
            ))}
          </nav>
        </aside>

        {/* Settings Content */}
        <main className="lg:col-span-9 mt-8 lg:mt-0">
          <div className="space-y-8">
            {/* Notifications */}
            {selectedSection === 'notifications' && (
              <div className="card">
                <div className="card-header">
                  <h2 className="text-lg font-semibold text-secondary-900">Notification Preferences</h2>
                  <p className="text-sm text-secondary-600">
                    Choose how you want to be notified about updates and activities
                  </p>
                </div>
                <div className="card-content space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-secondary-900">Email Notifications</h3>
                      <p className="text-sm text-secondary-600">
                        Receive notifications via email
                      </p>
                    </div>
                    <button
                      onClick={() => handleNotificationChange('email', !currentSettings.notifications.email)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        currentSettings.notifications.email ? 'bg-primary-600' : 'bg-secondary-200'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          currentSettings.notifications.email ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-secondary-900">Push Notifications</h3>
                      <p className="text-sm text-secondary-600">
                        Receive push notifications in your browser
                      </p>
                    </div>
                    <button
                      onClick={() => handleNotificationChange('push', !currentSettings.notifications.push)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        currentSettings.notifications.push ? 'bg-primary-600' : 'bg-secondary-200'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          currentSettings.notifications.push ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-secondary-900">Chat Notifications</h3>
                      <p className="text-sm text-secondary-600">
                        Get notified about new chat messages and responses
                      </p>
                    </div>
                    <button
                      onClick={() => handleNotificationChange('chat', !currentSettings.notifications.chat)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        currentSettings.notifications.chat ? 'bg-primary-600' : 'bg-secondary-200'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          currentSettings.notifications.chat ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>

                  {(user?.role === 'manager' || user?.role === 'admin') && (
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-sm font-medium text-secondary-900">Approval Notifications</h3>
                        <p className="text-sm text-secondary-600">
                          Get notified about approval requests and updates
                        </p>
                      </div>
                      <button
                        onClick={() => handleNotificationChange('approvals', !currentSettings.notifications.approvals)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          currentSettings.notifications.approvals ? 'bg-primary-600' : 'bg-secondary-200'
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            currentSettings.notifications.approvals ? 'translate-x-6' : 'translate-x-1'
                          }`}
                        />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Appearance */}
            {selectedSection === 'appearance' && (
              <div className="card">
                <div className="card-header">
                  <h2 className="text-lg font-semibold text-secondary-900">Appearance</h2>
                  <p className="text-sm text-secondary-600">
                    Customize how Aura looks and feels
                  </p>
                </div>
                <div className="card-content space-y-6">
                  <div>
                    <h3 className="text-sm font-medium text-secondary-900 mb-4">Theme</h3>
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { value: 'light', label: 'Light', icon: SunIcon },
                        { value: 'dark', label: 'Dark', icon: MoonIcon },
                        { value: 'auto', label: 'Auto', icon: ComputerDesktopIcon },
                      ].map((theme) => (
                        <button
                          key={theme.value}
                          onClick={() => handlePreferenceChange('theme', theme.value)}
                          className={`relative p-4 border rounded-lg text-center hover:border-primary-300 transition-colors ${
                            currentSettings.preferences.theme === theme.value
                              ? 'border-primary-500 bg-primary-50'
                              : 'border-secondary-200'
                          }`}
                        >
                          <div className="flex flex-col items-center space-y-2">
                            <theme.icon className="h-6 w-6 text-secondary-600" />
                            <span className="text-sm font-medium text-secondary-900">
                              {theme.label}
                            </span>
                          </div>
                          {currentSettings.preferences.theme === theme.value && (
                            <div className="absolute top-2 right-2">
                              <CheckIcon className="h-4 w-4 text-primary-600" />
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Language & Region */}
            {selectedSection === 'language' && (
              <div className="card">
                <div className="card-header">
                  <h2 className="text-lg font-semibold text-secondary-900">Language & Region</h2>
                  <p className="text-sm text-secondary-600">
                    Set your language, timezone, and regional preferences
                  </p>
                </div>
                <div className="card-content space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Language
                    </label>
                    <select
                      value={currentSettings.preferences.language}
                      onChange={(e) => handlePreferenceChange('language', e.target.value)}
                      className="input"
                    >
                      <option value="en">English</option>
                      <option value="es">Spanish</option>
                      <option value="fr">French</option>
                      <option value="de">German</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Timezone
                    </label>
                    <select
                      value={currentSettings.preferences.timezone}
                      onChange={(e) => handlePreferenceChange('timezone', e.target.value)}
                      className="input"
                    >
                      <option value="UTC">UTC</option>
                      <option value="America/New_York">Eastern Time</option>
                      <option value="America/Chicago">Central Time</option>
                      <option value="America/Denver">Mountain Time</option>
                      <option value="America/Los_Angeles">Pacific Time</option>
                      <option value="Europe/London">London</option>
                      <option value="Europe/Paris">Paris</option>
                      <option value="Asia/Tokyo">Tokyo</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Date Format
                    </label>
                    <select
                      value={currentSettings.preferences.dateFormat}
                      onChange={(e) => handlePreferenceChange('dateFormat', e.target.value)}
                      className="input"
                    >
                      <option value="MM/dd/yyyy">MM/DD/YYYY</option>
                      <option value="dd/MM/yyyy">DD/MM/YYYY</option>
                      <option value="yyyy-MM-dd">YYYY-MM-DD</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Privacy */}
            {selectedSection === 'privacy' && (
              <div className="card">
                <div className="card-header">
                  <h2 className="text-lg font-semibold text-secondary-900">Privacy Settings</h2>
                  <p className="text-sm text-secondary-600">
                    Control your privacy and data sharing preferences
                  </p>
                </div>
                <div className="card-content space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-secondary-900">Profile Visibility</h3>
                      <p className="text-sm text-secondary-600">
                        Make your profile visible to other team members
                      </p>
                    </div>
                    <button
                      onClick={() => handlePrivacyChange('profileVisible', !currentSettings.privacy.profileVisible)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        currentSettings.privacy.profileVisible ? 'bg-primary-600' : 'bg-secondary-200'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          currentSettings.privacy.profileVisible ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-secondary-900">Activity Tracking</h3>
                      <p className="text-sm text-secondary-600">
                        Allow Aura to track your activity for improved recommendations
                      </p>
                    </div>
                    <button
                      onClick={() => handlePrivacyChange('activityTracking', !currentSettings.privacy.activityTracking)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        currentSettings.privacy.activityTracking ? 'bg-primary-600' : 'bg-secondary-200'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          currentSettings.privacy.activityTracking ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Connection Status */}
            <div className="bg-secondary-50 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-success-500' : 'bg-danger-500'}`} />
                <div>
                  <p className="text-sm font-medium text-secondary-900">
                    Real-time Connection: {isConnected ? 'Connected' : 'Disconnected'}
                  </p>
                  <p className="text-xs text-secondary-600">
                    {isConnected 
                      ? 'You will receive real-time notifications and updates'
                      : 'Real-time features are currently unavailable'
                    }
                  </p>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}