export default function LoadingPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-secondary-50">
      <div className="text-center">
        <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center animate-pulse">
          <span className="text-white font-bold text-xl">A</span>
        </div>
        <div className="space-y-3">
          <div className="flex justify-center">
            <div className="w-8 h-8 loading-spinner border-primary-600" />
          </div>
          <h2 className="text-lg font-medium text-secondary-900">Loading Aura...</h2>
          <p className="text-sm text-secondary-600">Please wait while we initialize your onboarding assistant</p>
        </div>
      </div>
    </div>
  )
}