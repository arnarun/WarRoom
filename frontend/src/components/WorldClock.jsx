import { useState, useEffect } from 'react'

const ZONES = [
  { label: 'IST',  tz: 'Asia/Kolkata' },
  { label: 'EST',  tz: 'America/New_York' },
  { label: 'CET',  tz: 'Europe/Paris' },
  { label: 'SWE',  tz: 'Europe/Stockholm' },
]

function formatTime(tz) {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: tz,
    hour:     '2-digit',
    minute:   '2-digit',
    second:   '2-digit',
    hour12:   false,
  }).format(new Date())
}

export default function WorldClock() {
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="flex items-center gap-4 text-[11px] font-mono">
      {ZONES.map(z => (
        <span key={z.label} className="flex items-center gap-1">
          <span className="text-gray-600 uppercase">{z.label}</span>
          <span className="text-gray-300 tabular-nums">{formatTime(z.tz)}</span>
        </span>
      ))}
    </div>
  )
}
