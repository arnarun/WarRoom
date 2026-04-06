import { useState, useEffect, useCallback } from 'react'
import api from '../lib/api'

export function useOsint(filters = {}, interval = 60000) {
  const [signals,   setSignals]   = useState([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)

  const fetch = useCallback(async () => {
    try {
      const params = Object.fromEntries(
        Object.entries(filters).filter(([_, v]) => v != null && v !== '')
      )
      const { data } = await api.get('/osint', { params })
      setSignals(data)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(filters)])

  useEffect(() => {
    fetch()
    const id = setInterval(fetch, interval)
    return () => clearInterval(id)
  }, [fetch, interval])

  return { signals, loading, error, refetch: fetch }
}
