import { useEffect, useMemo, useState } from 'react'
import { getResearchUniverse } from '../../api/researchApi'

function UniverseConfig({ value, onChange }) {
  const [universeData, setUniverseData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadUniverse() {
      try {
        setLoading(true)
        const data = await getResearchUniverse()
        setUniverseData(data)
      } catch (err) {
        setError(err.message || 'Failed to load universe')
      } finally {
        setLoading(false)
      }
    }

    loadUniverse()
  }, [])

  const rows = universeData?.universe || []

  const filterOptions = useMemo(() => {
    const unique = (key) =>
      [...new Set(
        rows
          .map((row) => row[key])
          .filter((value) => value && String(value).trim())
          .map((value) => String(value).trim())
      )].sort()

    return {
      macro_sector: unique('MACRO_ECONOMIC_SECTOR'),
      sector: unique('SECTOR'),
      industry: unique('INDUSTRY'),
      basic_industry: unique('BASIC_INDUSTRY'),
    }
  }, [rows])

  const type = value?.type || 'all_stocks'
  const selectedValue = value?.value || ''

  function updateType(newType) {
    onChange({
      type: newType,
      value: '',
      symbols: [],
    })
  }

  function updateValue(newValue) {
    onChange({
      ...value,
      value: newValue,
    })
  }

  return (
    <div className="config-card">
      <label>Universe</label>

      <select
        value={type}
        onChange={(event) => updateType(event.target.value)}
      >
        <option value="all_stocks">All Stocks</option>
        <option value="major_stocks">Major Stocks</option>
        <option value="macro_sector">Macro Sector</option>
        <option value="sector">Sector</option>
        <option value="industry">Industry</option>
        <option value="basic_industry">Basic Industry</option>
        <option value="symbols">Custom Symbols</option>
      </select>

      {loading && (
        <span className="field-help">
          Loading research universe...
        </span>
      )}

      {error && (
        <span className="field-help">
          {error}
        </span>
      )}

      {type !== 'all_stocks' &&
        type !== 'symbols' &&
        type !== 'major_stocks' &&
        !loading && (
          <select
            value={selectedValue}
            onChange={(event) => updateValue(event.target.value)}
          >
            <option value="">
              Select {type.replace('_', ' ')}
            </option>

            {filterOptions[type].map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        )}

      {type === 'symbols' && (
        <input
          type="text"
          placeholder="RELIANCE, TCS, INFY"
          value={value?.symbols?.join(', ') || ''}
          onChange={(event) => {
            const symbols = event.target.value
              .split(',')
              .map((symbol) => symbol.trim().toUpperCase())
              .filter(Boolean)

            onChange({
              type: 'symbols',
              value: '',
              symbols,
            })
          }}
        />
      )}

      <span className="field-help">
        {type === 'all_stocks'
          ? `${universeData?.total_stocks || 0} stocks in current research universe`
          : type === 'major_stocks'
            ? `${universeData?.major_stocks_total || 0} Nifty 500 stocks`
            : 'Filter the current research universe.'}
      </span>
    </div>
  )
}

export default UniverseConfig