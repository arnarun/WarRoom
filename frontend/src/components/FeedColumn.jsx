export default function FeedColumn({ title, icon, count, children, className = '' }) {
  return (
    <div className={`flex flex-col min-w-[320px] max-w-[360px] h-full ${className}`}>
      {/* Column header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-800 bg-gray-900 sticky top-0 z-10">
        {icon && <span>{icon}</span>}
        <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">{title}</span>
        {count != null && (
          <span className="ml-auto text-[10px] text-gray-600">{count} items</span>
        )}
      </div>
      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2 feed-fade">
        {children}
      </div>
    </div>
  )
}
