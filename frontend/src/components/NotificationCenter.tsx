import { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { XMarkIcon, BellIcon, CheckIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { useWebSocket } from '@/contexts/WebSocketContext'
import { formatDistanceToNow } from 'date-fns'

interface NotificationCenterProps {
  open: boolean
  onClose: () => void
}

export default function NotificationCenter({ open, onClose }: NotificationCenterProps) {
  const { notifications, clearNotifications } = useWebSocket()

  const getNotificationIcon = (type: string, priority: string) => {
    if (priority === 'critical') {
      return <ExclamationTriangleIcon className="h-5 w-5 text-danger-500" />
    }
    
    switch (type) {
      case 'chat_message':
        return <BellIcon className="h-5 w-5 text-primary-500" />
      case 'task_update':
        return <CheckIcon className="h-5 w-5 text-success-500" />
      case 'approval_request':
        return <ExclamationTriangleIcon className="h-5 w-5 text-warning-500" />
      case 'system_alert':
        return <BellIcon className="h-5 w-5 text-secondary-500" />
      default:
        return <BellIcon className="h-5 w-5 text-secondary-500" />
    }
  }

  const getNotificationBorder = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'border-l-4 border-danger-500'
      case 'high':
        return 'border-l-4 border-warning-500'
      case 'medium':
        return 'border-l-4 border-primary-500'
      default:
        return 'border-l-4 border-secondary-300'
    }
  }

  const sortedNotifications = notifications.sort((a, b) => 
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  )

  return (
    <Transition.Root show={open} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-in-out duration-500"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in-out duration-500"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-secondary-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10 sm:pl-16">
              <Transition.Child
                as={Fragment}
                enter="transform transition ease-in-out duration-500 sm:duration-700"
                enterFrom="translate-x-full"
                enterTo="translate-x-0"
                leave="transform transition ease-in-out duration-500 sm:duration-700"
                leaveFrom="translate-x-0"
                leaveTo="translate-x-full"
              >
                <Dialog.Panel className="pointer-events-auto w-screen max-w-md">
                  <div className="flex h-full flex-col bg-white shadow-xl">
                    <div className="px-4 py-6 sm:px-6">
                      <div className="flex items-start justify-between">
                        <Dialog.Title className="text-lg font-medium text-secondary-900">
                          Notifications
                        </Dialog.Title>
                        <div className="ml-3 flex h-7 items-center">
                          <button
                            type="button"
                            className="rounded-md bg-white text-secondary-400 hover:text-secondary-500 focus:ring-2 focus:ring-primary-500"
                            onClick={onClose}
                          >
                            <span className="sr-only">Close panel</span>
                            <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="border-b border-secondary-200 px-4 py-2 sm:px-6">
                      <div className="flex items-center justify-between">
                        <p className="text-sm text-secondary-600">
                          {notifications.length} notification{notifications.length !== 1 ? 's' : ''}
                        </p>
                        {notifications.length > 0 && (
                          <button
                            type="button"
                            className="text-sm text-primary-600 hover:text-primary-500"
                            onClick={clearNotifications}
                          >
                            Clear all
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="flex-1 overflow-y-auto">
                      {sortedNotifications.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-64 text-center">
                          <BellIcon className="h-12 w-12 text-secondary-300 mb-4" />
                          <h3 className="text-sm font-medium text-secondary-900 mb-1">
                            No notifications
                          </h3>
                          <p className="text-sm text-secondary-500">
                            You'll see notifications here when they arrive
                          </p>
                        </div>
                      ) : (
                        <div className="divide-y divide-secondary-200">
                          {sortedNotifications.map((notification) => (
                            <div
                              key={notification.id}
                              className={`px-4 py-4 sm:px-6 hover:bg-secondary-50 ${getNotificationBorder(notification.priority)}`}
                            >
                              <div className="flex space-x-3">
                                <div className="flex-shrink-0">
                                  {getNotificationIcon(notification.type, notification.priority)}
                                </div>
                                <div className="flex-1 space-y-1">
                                  <div className="flex items-center justify-between">
                                    <h3 className="text-sm font-medium text-secondary-900">
                                      {notification.data.message || notification.type.replace('_', ' ')}
                                    </h3>
                                    <p className="text-xs text-secondary-500">
                                      {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}
                                    </p>
                                  </div>
                                  
                                  {notification.data.description && (
                                    <p className="text-sm text-secondary-600">
                                      {notification.data.description}
                                    </p>
                                  )}
                                  
                                  {notification.data.task_id && (
                                    <p className="text-xs text-secondary-500">
                                      Task: {notification.data.task_id}
                                    </p>
                                  )}
                                  
                                  {notification.data.action_type && (
                                    <p className="text-xs text-secondary-500">
                                      Action: {notification.data.action_type}
                                    </p>
                                  )}
                                  
                                  <div className="flex items-center space-x-2">
                                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                      notification.priority === 'critical' ? 'bg-danger-100 text-danger-800' :
                                      notification.priority === 'high' ? 'bg-warning-100 text-warning-800' :
                                      notification.priority === 'medium' ? 'bg-primary-100 text-primary-800' :
                                      'bg-secondary-100 text-secondary-800'
                                    }`}>
                                      {notification.priority}
                                    </span>
                                    
                                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-secondary-100 text-secondary-800">
                                      {notification.type.replace('_', ' ')}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}