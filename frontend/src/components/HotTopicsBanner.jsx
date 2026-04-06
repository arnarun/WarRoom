import { useState, useEffect, useRef, useCallback } from 'react'
import { useHotTopics } from '../hooks/useHotTopics'

const CAT_GRADIENTS = {
  politics:         'from-blue-900/90 to-blue-950/95',
  geopolitics:      'from-orange-900/90 to-orange-950/95',
  business:         'from-yellow-900/90 to-yellow-950/95',
  technology:       'from-cyan-900/90 to-cyan-950/95',
  security:         'from-red-900/90 to-red-950/95',
  defense:          'from-red-900/90 to-gray-950/95',
  health:           'from-green-900/90 to-green-950/95',
  emergency:        'from-red-800/90 to-red-950/98',
  startups:         'from-purple-900/90 to-purple-950/95',
  'venture-capital':'from-pink-900/90 to-pink-950/95',
  science:          'from-teal-900/90 to-teal-950/95',
}

const CAT_BADGE = {
  politics:         'bg-blue-500/20 text-blue-300 border-blue-600',
  geopolitics:      'bg-orange-500/20 text-orange-300 border-orange-600',
  business:         'bg-yellow-500/20 text-yellow-300 border-yellow-600',
  technology:       'bg-cyan-500/20 text-cyan-300 border-cyan-600',
  security:         'bg-red-500/20 text-red-300 border-red-600',
  defense:          'bg-red-500/20 text-red-200 border-red-700',
  health:           'bg-green-500/20 text-green-300 border-green-600',
  emergency:        'bg-red-500/30 text-red-200 border-red-500',
  startups:         'bg-purple-500/20 text-purple-300 border-purple-600',
  'venture-capital':'bg-pink-500/20 text-pink-300 border-pink-600',
  science:          'bg-teal-500/20 text-teal-300 border-teal-600',
}

const CAT_ICONS = {
  politics:'🗳', geopolitics:'🌍', business:'📈', technology:'💻',
  security:'🔐', defense:'⚔️', health:'🏥', emergency:'🚨',
  startups:'🚀', 'venture-capital':'💰', science:'🔬', other:'📰',
}

function timeAgo(iso) {
  if (!iso) return ''
  const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (m < 1)  return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  return h < 24 ? `${h}h ago` : `${Math.floor(h / 24)}d ago`
}

export default function HotTopicsBanner() {
  const { topics, loading } = useHotTopics(8, 180000)
  const [idx,     setIdx]   = useState(0)
  const timerRef            = useRef(null)

  // Prefer articles with images; fallback to any article
  const withImg    = topics.filter(a => a.image_url)
  const candidates = withImg.length >= 4 ? withImg : topics
  const slides     = candidates.slice(0, 12)

  const goTo = useCallback((next) => {
    setIdx(next)
  }, [])

  const startTimer = useCallback(() => {
    clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setIdx(i => (i + 1) % slides.length)
    }, 5000)
  }, [slides.length])

  useEffect(() => {
    if (slides.length > 1) startTimer()
    return () => clearInterval(timerRef.current)
  }, [slides.length, startTimer])

  const handleNav = (next) => {
    goTo((next + slides.length) % slides.length)
    startTimer()   // reset timer on manual nav
  }

  if (loading || slides.length === 0) return null

  const article = slides[idx]
  const grad    = CAT_GRADIENTS[article.category] || 'from-gray-900/90 to-gray-950/95'
  const badge   = CAT_BADGE[article.category]     || 'bg-gray-700 text-gray-300 border-gray-600'
  const icon    = CAT_ICONS[article.category]     || '📰'

  return (
    <div className="relative w-full h-52 overflow-hidden bg-gray-950 border-b border-gray-800 select-none">

      {/* Slides track — all slides side by side, translate to show current */}
      <div
        className="flex h-full"
        style={{
          width:     `${slides.length * 100}%`,
          transform: `translateX(-${(idx * 100) / slides.length}%)`,
          transition: 'transform 0.55s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        {slides.map((a, i) => {
          const g = CAT_GRADIENTS[a.category] || 'from-gray-900/90 to-gray-950/95'
          return (
            <a
              key={a.id}
              href={a.url}
              target="_blank"
              rel="noopener noreferrer"
              className="relative flex-none h-full"
              style={{ width: `${100 / slides.length}%` }}
            >
              {/* Background image */}
              {a.image_url ? (
                <img
                  src={a.image_url}
                  alt=""
                  className="absolute inset-0 w-full h-full object-cover"
                  onError={e => { e.target.style.display = 'none' }}
                />
              ) : (
                /* No image — solid category gradient */
                <div className={`absolute inset-0 bg-gradient-to-br ${g} opacity-60`} />
              )}

              {/* Dark gradient overlay for text legibility */}
              <div className="absolute inset-0 bg-gradient-to-t from-gray-950 via-gray-950/60 to-transparent" />
              <div className="absolute inset-0 bg-gradient-to-r from-gray-950/70 via-transparent to-transparent" />

              {/* Content */}
              <div className="absolute inset-0 flex flex-col justify-end p-5 gap-2">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-bold uppercase tracking-wider border rounded px-2 py-0.5 ${CAT_BADGE[a.category] || 'bg-gray-700 text-gray-300 border-gray-600'}`}>
                    {CAT_ICONS[a.category] || '📰'} {a.category || 'news'}
                  </span>
                  <span className="text-[11px] text-gray-400 font-semibold">{a.source}</span>
                  {a.country && (
                    <span className="text-[10px] text-gray-600">{a.country}</span>
                  )}
                  <span className="text-[10px] text-gray-600 ml-auto">{timeAgo(a.published_at)}</span>
                </div>
                <h2 className="text-base font-bold text-white leading-snug line-clamp-2 max-w-2xl drop-shadow">
                  {a.title}
                </h2>
                {a.summary && (
                  <p className="text-xs text-gray-400 line-clamp-1 max-w-xl">{a.summary}</p>
                )}
              </div>
            </a>
          )
        })}
      </div>

      {/* Prev / Next arrows */}
      {slides.length > 1 && (
        <>
          <button
            onClick={e => { e.preventDefault(); handleNav(idx - 1) }}
            className="absolute left-3 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/40 border border-gray-700 flex items-center justify-center text-gray-300 hover:bg-black/70 hover:text-white transition z-10"
          >
            ‹
          </button>
          <button
            onClick={e => { e.preventDefault(); handleNav(idx + 1) }}
            className="absolute right-3 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/40 border border-gray-700 flex items-center justify-center text-gray-300 hover:bg-black/70 hover:text-white transition z-10"
          >
            ›
          </button>
        </>
      )}

      {/* Dot indicators */}
      {slides.length > 1 && (
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1.5 z-10">
          {slides.map((_, i) => (
            <button
              key={i}
              onClick={() => handleNav(i)}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                i === idx ? 'w-5 bg-white' : 'w-1.5 bg-gray-600 hover:bg-gray-400'
              }`}
            />
          ))}
        </div>
      )}

      {/* Live indicator */}
      <div className="absolute top-3 left-4 flex items-center gap-1.5 z-10">
        <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
        <span className="text-[10px] font-bold text-red-400 uppercase tracking-widest">Live</span>
      </div>
    </div>
  )
}
