import { useState, useEffect, useRef } from 'react'

export function useMarket() {
  const [prices,    setPrices]    = useState([])
  const [connected, setConnected] = useState(false)
  const [error,     setError]     = useState(null)
  const esRef = useRef(null)

  useEffect(() => {
    function connect() {
      const sseBase = import.meta.env.VITE_API_URL || ''
      const es = new EventSource(`${sseBase}/api/stream/prices`)
      esRef.current = es

      es.onopen = () => {
        setConnected(true)
        setError(null)
      }
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          if (!data.error) setPrices(data)
        } catch {}
      }
      es.onerror = () => {
        setConnected(false)
        setError('SSE disconnected, retrying…')
        es.close()
        setTimeout(connect, 5000)
      }
    }
    connect()
    return () => esRef.current?.close()
  }, [])

  return { prices, connected, error }
}
