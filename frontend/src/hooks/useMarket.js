import { useState, useEffect } from 'react'
import api from '../lib/api'

export function useMarket() {
  const [prices,    setPrices]    = useState([])
  const [connected, setConnected] = useState(false)
  const [error,     setError]     = useState(null)

  useEffect(() => {
    async function fetchPrices() {
      try {
        const { data } = await api.get('/market')
        if (Array.isArray(data)) {
          setPrices(data)
          setConnected(true)
          setError(null)
        }
      } catch (e) {
        setConnected(false)
        setError('Market data unavailable')
      }
    }

    fetchPrices()
    const id = setInterval(fetchPrices, 30000)
    return () => clearInterval(id)
  }, [])

  return { prices, connected, error }
}
