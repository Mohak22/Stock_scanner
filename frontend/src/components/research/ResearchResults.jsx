import { useMemo, useState } from 'react'

function ResearchResults({ researchResult, onSaveExperiment }) {
  const [activeAnalysisTab, setActiveAnalysisTab] = useState('stock')
  const [activeStage, setActiveStage] = useState('development')

  const [sortConfig, setSortConfig] = useState({
    key: 'TIMESTAMP',
    direction: 'desc',
  })

  const [showRawResponse, setShowRawResponse] = useState(false)

  /*
   * ----------------------------------------------------------
   * SAFE DEFAULTS
   * ----------------------------------------------------------
   */

  const stageResult = researchResult?.[activeStage] || {}
  const summary = stageResult.summary || {}
  const diagnostics = stageResult.diagnostics || {}
  const performance = stageResult.performance || {}
  const analysis = stageResult.analysis || {}

  const byFeature = analysis.by_feature || {}
  const byMarketRegime = analysis.by_market_regime || {}

  /*
   * ----------------------------------------------------------
   * SIGNAL-LEVEL DATA
   *
   * One row = one stock + one signal date.
   *
   * No aggregation by stock.
   * ----------------------------------------------------------
   */

  const signalRows = Array.isArray(stageResult.signals)
    ? stageResult.signals
    : []

  /*
   * ----------------------------------------------------------
   * REQUESTED HORIZONS
   * ----------------------------------------------------------
   */

  const requestedHorizons = Object.keys(performance)
    .map((key) =>
      Number(String(key).replace('T+', ''))
    )
    .filter(Number.isFinite)
    .sort((a, b) => a - b)

  const primaryAnalysisHorizon =
    requestedHorizons.includes(5)
      ? 5
      : requestedHorizons[requestedHorizons.length - 1]

  /*
   * ----------------------------------------------------------
   * SORT SIGNAL ROWS
   * ----------------------------------------------------------
   */

  const sortedSignalRows = useMemo(() => {
    if (signalRows.length === 0) {
      return []
    }

    const rows = [...signalRows]

    rows.sort((a, b) => {
      let valueA
      let valueB

      /*
       * STOCK
       */

      if (sortConfig.key === 'SYMBOL') {
        valueA = String(a.SYMBOL ?? '')
        valueB = String(b.SYMBOL ?? '')

        const comparison = valueA.localeCompare(
          valueB,
          undefined,
          {
            sensitivity: 'base',
          }
        )

        return sortConfig.direction === 'asc'
          ? comparison
          : -comparison
      }

      /*
       * SIGNAL DATE
       */

      if (sortConfig.key === 'TIMESTAMP') {
        valueA = new Date(
          a.TIMESTAMP
        ).getTime()

        valueB = new Date(
          b.TIMESTAMP
        ).getTime()

        if (!Number.isFinite(valueA)) {
          valueA = -Infinity
        }

        if (!Number.isFinite(valueB)) {
          valueB = -Infinity
        }
      }

      /*
       * FORWARD RETURN
       */

      else {
        valueA = Number(
          a[`RETURN_T${sortConfig.key}`]
        )

        valueB = Number(
          b[`RETURN_T${sortConfig.key}`]
        )

        if (!Number.isFinite(valueA)) {
          valueA = -Infinity
        }

        if (!Number.isFinite(valueB)) {
          valueB = -Infinity
        }
      }

      return sortConfig.direction === 'asc'
        ? valueA - valueB
        : valueB - valueA
    })

    return rows
  }, [signalRows, sortConfig])

  /*
   * ----------------------------------------------------------
   * SORT HANDLER
   * ----------------------------------------------------------
   */

  const handleSort = (key) => {
    setSortConfig((current) => ({
      key,
      direction:
        current.key === key &&
          current.direction === 'asc'
          ? 'desc'
          : 'asc',
    }))
  }

  /*
   * ----------------------------------------------------------
   * SORT INDICATOR
   * ----------------------------------------------------------
   */

  const sortIndicator = (key) => {
    if (sortConfig.key !== key) {
      return '↕'
    }

    return sortConfig.direction === 'asc'
      ? '↑'
      : '↓'
  }

  const [isSavingExperiment, setIsSavingExperiment] =
    useState(false)

  const [saveMessage, setSaveMessage] =
    useState('')

  /*
   * ----------------------------------------------------------
   * RAW RESPONSE
   *
   * IMPORTANT:
   *
   * Do NOT stringify the potentially large research result
   * unless the user explicitly opens the Raw Response section.
   * ----------------------------------------------------------
   */

  const rawResponse = useMemo(() => {
    if (!showRawResponse || !researchResult) {
      return ''
    }

    return JSON.stringify(
      researchResult,
      null,
      2
    )
  }, [showRawResponse, researchResult])

  const handleSaveExperiment = async () => {
    if (!researchResult || isSavingExperiment) {
      return
    }

    try {
      setIsSavingExperiment(true)
      setSaveMessage('')

      const result = await onSaveExperiment(
        researchResult
      )

      setSaveMessage(
        `Saved as ${result.experiment_id}`
      )
    } catch (error) {
      setSaveMessage(
        error.message ||
        'Failed to save experiment.'
      )
    } finally {
      setIsSavingExperiment(false)
    }
  }

  /*
   * ----------------------------------------------------------
   * NO RESULT YET
   *
   * This comes AFTER all hooks.
   * ----------------------------------------------------------
   */

  if (!researchResult) {
    return null
  }

  return (
    <div className="research-results">

      {/* =====================================================
          RESEARCH OUTPUT HEADER
          ===================================================== */}

      <div className="results-header">

        <div>

          <span className="section-kicker">
            RESEARCH OUTPUT
          </span>

          <h2>
            Research Completed
          </h2>

          <p>
            The backend successfully executed the configured
            research experiment.
          </p>

        </div>

        <div className="results-header-actions">

          <button
            className="save-experiment-button"
            onClick={handleSaveExperiment}
            disabled={isSavingExperiment}
          >
            {isSavingExperiment
              ? 'SAVING...'
              : 'SAVE AS EXPERIMENT'}
          </button>

          <div className="research-status success">
            <span className="status-dot"></span>
            COMPLETE
          </div>

        </div>

      </div>

      {saveMessage && (
        <div
          className={
            saveMessage.startsWith('Saved as')
              ? 'experiment-save-message success'
              : 'experiment-save-message error'
          }
        >
          {saveMessage}
        </div>
      )}
      
      <div className="analysis-tabs research-stage-tabs">
        {[
          ['development', 'DEVELOPMENT', 'Iterate and inspect the hypothesis'],
          ['validation', 'VALIDATION', 'Unseen period for candidate evaluation'],
          ['final_holdout', 'FINAL HOLDOUT', 'Untouched evidence before locking'],
        ].map(([value, label, help]) => (
          <button
            key={value}
            className={`analysis-tab ${activeStage === value ? 'active' : ''}`}
            onClick={() => setActiveStage(value)}
            disabled={!researchResult?.[value]}
          >
            <span className="tab-number">
              {value === 'development' ? '01' : value === 'validation' ? '02' : '03'}
            </span>
            <span>
              <strong>{label}</strong>
              <small>{researchResult?.[value] ? help : 'Not evaluated'}</small>
            </span>
          </button>
        ))}
      </div>

            {/* =====================================================
          SUMMARY
          ===================================================== */}

      <div className="results-grid">

        <div className="result-card">

          <span>
            Signals
          </span>

          <strong>
            {summary.signal_count?.toLocaleString() ?? '—'}
          </strong>

        </div>


        <div className="result-card">

          <span>
            Signal Rate
          </span>

          <strong>
            {summary.signal_rate != null
              ? `${summary.signal_rate.toFixed(2)}%`
              : '—'}
          </strong>

        </div>

        <div className="result-card">
          <span>
            Stocks With Signals
          </span>

          <strong>
            {diagnostics.stocks_with_signals?.toLocaleString() ?? '—'}
          </strong>
        </div>

        <div className="result-card">

          <span>
            Sample Quality
          </span>

          <strong>
            {diagnostics.sample_quality?.classification ?? '—'}
          </strong>

        </div>

      </div>


      {/* =====================================================
          PERFORMANCE ANALYSIS
          ===================================================== */}

      <div className="result-section">

        <div className="section-heading">

          <div>

            <span className="section-kicker">
              PERFORMANCE ANALYSIS
            </span>

            <h3>
              Forward Return Performance
            </h3>

          </div>

          <span className="section-meta">
            {Object.keys(performance).length} horizons evaluated
          </span>

        </div>


        {/* =================================================
            PERFORMANCE CARDS
            ================================================= */}

        <div className="performance-grid">

          {Object.entries(performance).map(
            ([horizon, metrics]) => (

              <div
                className="performance-card"
                key={horizon}
              >

                <div className="performance-card-header">

                  <span className="horizon-label">
                    {horizon}
                  </span>

                  <span className="observation-count">

                    {metrics.observations?.toLocaleString() ?? '—'}

                    {' '}

                    observations

                  </span>

                </div>


                <div className="primary-performance">

                  <span>
                    Average Return
                  </span>

                  <strong
                    className={
                      metrics.average_return >= 0
                        ? 'positive-value'
                        : 'negative-value'
                    }
                  >

                    {metrics.average_return != null
                      ? `${metrics.average_return.toFixed(2)}%`
                      : '—'}

                  </strong>

                </div>


                <div className="performance-metrics">

                  <div>

                    <span>
                      Median
                    </span>

                    <strong>
                      {metrics.median_return?.toFixed(2) ?? '—'}%
                    </strong>

                  </div>


                  <div>

                    <span>
                      Positive
                    </span>

                    <strong>
                      {metrics.positive_return_pct?.toFixed(2) ?? '—'}%
                    </strong>

                  </div>


                  <div>

                    <span>
                      Excess vs NIFTY
                    </span>

                    <strong
                      className={
                        metrics.average_excess_return >= 0
                          ? 'positive-value'
                          : 'negative-value'
                      }
                    >
                      {metrics.average_excess_return?.toFixed(2) ?? '—'}%
                    </strong>

                  </div>


                  <div>

                    <span>
                      Outperformed
                    </span>

                    <strong>
                      {metrics.outperformed_market_pct?.toFixed(2) ?? '—'}%
                    </strong>

                  </div>


                  <div>

                    <span>
                      Best
                    </span>

                    <strong className="positive-value">
                      {metrics.best_return?.toFixed(2) ?? '—'}%
                    </strong>

                  </div>


                  <div>

                    <span>
                      Worst
                    </span>

                    <strong className="negative-value">
                      {metrics.worst_return?.toFixed(2) ?? '—'}%
                    </strong>

                  </div>

                </div>

              </div>

            )
          )}

        </div>


        {/* =================================================
            PERFORMANCE TABLE
            ================================================= */}

        <div className="performance-table-wrapper">

          <table className="performance-table">

            <thead>

              <tr>

                <th>
                  Horizon
                </th>

                <th>
                  Avg Return
                </th>

                <th>
                  Median
                </th>

                <th>
                  Positive
                </th>

                <th>
                  Avg NIFTY
                </th>

                <th>
                  Excess Return
                </th>

                <th>
                  Outperformed
                </th>

              </tr>

            </thead>


            <tbody>

              {Object.entries(performance).map(
                ([horizon, metrics]) => (

                  <tr key={horizon}>

                    <td className="table-horizon">
                      {horizon}
                    </td>

                    <td
                      className={
                        metrics.average_return >= 0
                          ? 'positive-value'
                          : 'negative-value'
                      }
                    >
                      {metrics.average_return?.toFixed(2) ?? '—'}%
                    </td>

                    <td>
                      {metrics.median_return?.toFixed(2) ?? '—'}%
                    </td>

                    <td>
                      {metrics.positive_return_pct?.toFixed(2) ?? '—'}%
                    </td>

                    <td>
                      {metrics.average_market_return?.toFixed(2) ?? '—'}%
                    </td>

                    <td
                      className={
                        metrics.average_excess_return >= 0
                          ? 'positive-value'
                          : 'negative-value'
                      }
                    >
                      {metrics.average_excess_return?.toFixed(2) ?? '—'}%
                    </td>

                    <td>
                      {metrics.outperformed_market_pct?.toFixed(2) ?? '—'}%
                    </td>

                  </tr>

                )
              )}

            </tbody>

          </table>

        </div>

      </div>


      {/* =====================================================
          RESEARCH INTELLIGENCE
          ===================================================== */}

      <div className="analysis-section">

        <div className="analysis-header">

          <div>

            <span className="section-kicker">
              RESEARCH INTELLIGENCE
            </span>

            <h3>
              Signal Analysis
            </h3>

            <p>
              Decompose the research result across stocks,
              features and market regimes.
            </p>

          </div>


          <div className="analysis-live-indicator">

            <span className="analysis-pulse"></span>

            ANALYSIS READY

          </div>

        </div>


        {/* =================================================
            ANALYSIS TABS
            ================================================= */}

        <div className="analysis-tabs">

          <button
            className={`analysis-tab ${activeAnalysisTab === 'stock'
              ? 'active'
              : ''
              }`}
            onClick={() =>
              setActiveAnalysisTab('stock')
            }
          >

            <span className="tab-number">
              01
            </span>

            <span>

              <strong>
                By Stock
              </strong>

              <small>
                Signal-level behaviour
              </small>

            </span>

          </button>


          <button
            className={`analysis-tab ${activeAnalysisTab === 'feature'
              ? 'active'
              : ''
              }`}
            onClick={() =>
              setActiveAnalysisTab('feature')
            }
          >

            <span className="tab-number">
              02
            </span>

            <span>

              <strong>
                By Feature
              </strong>

              <small>
                Feature effectiveness
              </small>

            </span>

          </button>


          <button
            className={`analysis-tab ${activeAnalysisTab === 'regime'
              ? 'active'
              : ''
              }`}
            onClick={() =>
              setActiveAnalysisTab('regime')
            }
          >

            <span className="tab-number">
              03
            </span>

            <span>

              <strong>
                Market Regime
              </strong>

              <small>
                Contextual behaviour
              </small>

            </span>

          </button>

        </div>


        {/* =================================================
            STOCK ATTRIBUTION
            ================================================= */}

        {activeAnalysisTab === 'stock' && (

          <div className="analysis-panel">

            <div className="analysis-panel-top">

              <div>

                <span className="panel-kicker">
                  STOCK ATTRIBUTION
                </span>

                <h4>
                  Signal-Level Performance
                </h4>

                <p>
                  Every qualifying stock-date observation
                  and its forward returns.
                </p>

              </div>


              <div className="stock-analysis-summary">

                <span>
                  {signalRows.length.toLocaleString()}
                </span>

                {' '}

                observations

              </div>

            </div>


            <div className="stock-table-wrapper">

              <table className="stock-analysis-table">

                <thead>

                  <tr>

                    <th>

                      <button
                        type="button"
                        className="table-sort-button"
                        onClick={() =>
                          handleSort('SYMBOL')
                        }
                      >

                        Stock{' '}

                        {sortIndicator('SYMBOL')}

                      </button>

                    </th>


                    <th>

                      <button
                        type="button"
                        className="table-sort-button"
                        onClick={() =>
                          handleSort('TIMESTAMP')
                        }
                      >

                        Signal Date{' '}

                        {sortIndicator('TIMESTAMP')}

                      </button>

                    </th>


                    {requestedHorizons.map(
                      (horizon) => (

                        <th key={horizon}>

                          <button
                            type="button"
                            className="table-sort-button"
                            onClick={() =>
                              handleSort(horizon)
                            }
                          >

                            T+{horizon}{' '}

                            {sortIndicator(horizon)}

                          </button>

                        </th>

                      )
                    )}

                  </tr>

                </thead>


                <tbody>

                  {sortedSignalRows
                    .slice(0, 5)
                    .map(
                      (signal, index) => (

                        <tr
                          key={`${signal.SYMBOL}-${signal.TIMESTAMP}-${index}`}
                        >

                          {/* STOCK */}

                          <td>

                            <div className="stock-symbol">

                              <span className="stock-icon">
                                ◈
                              </span>

                              <strong>
                                {signal.SYMBOL ?? '—'}
                              </strong>

                            </div>

                          </td>


                          {/* SIGNAL DATE */}

                          <td className="signal-date">

                            {signal.TIMESTAMP ?? '—'}

                          </td>


                          {/* FORWARD RETURNS */}

                          {requestedHorizons.map(
                            (horizon) => {

                              const value = Number(
                                signal[
                                `RETURN_T${horizon}`
                                ]
                              )

                              const validValue =
                                Number.isFinite(value)

                              return (

                                <td
                                  key={horizon}
                                  className={
                                    !validValue
                                      ? ''
                                      : value >= 0
                                        ? 'positive-value'
                                        : 'negative-value'
                                  }
                                >

                                  {validValue
                                    ? `${value.toFixed(2)}%`
                                    : '—'}

                                </td>

                              )
                            }
                          )}

                        </tr>

                      )
                    )}


                  {sortedSignalRows.length === 0 && (

                    <tr>

                      <td
                        colSpan={
                          2 +
                          requestedHorizons.length
                        }
                        className="empty-analysis"
                      >

                        No signal observations are
                        available for this research run.

                      </td>

                    </tr>

                  )}

                </tbody>

              </table>

            </div>

          </div>

        )}


        {/* =================================================
            FEATURE ANALYSIS
            ================================================= */}

        {activeAnalysisTab === 'feature' && (

          <div className="analysis-panel">

            <div className="analysis-panel-top">

              <div>

                <span className="panel-kicker">
                  FEATURE ATTRIBUTION
                </span>

                <h4>
                  Performance by Feature
                </h4>

              </div>

              <div className="feature-intelligence">
                FEATURE → T+{primaryAnalysisHorizon} OUTCOME
              </div>

            </div>


            <div className="feature-analysis-grid">

              {Object.entries(byFeature).map(
                ([feature, data]) => {

                  const buckets =
                    data?.buckets || {}

                  return (

                    <div
                      className="feature-analysis-card"
                      key={feature}
                    >

                      <div className="feature-card-top">

                        <div className="feature-symbol">
                          ƒx
                        </div>

                        <div>

                          <strong>
                            {feature}
                          </strong>

                          <span>
                            Observed signal distribution
                          </span>

                        </div>

                      </div>


                      <div className="feature-card-body">

                        {Object.entries(
                          buckets
                        ).map(
                          ([bucket, bucketData]) => {

                            const result =
                              bucketData
                                ?.performance
                              ?.[`T+${primaryAnalysisHorizon}`]

                            return (

                              <div
                                className="feature-bucket"
                                key={bucket}
                              >

                                <div className="bucket-label">

                                  <span>
                                    {bucket}
                                  </span>

                                  <strong>
                                    {bucketData?.signal_count?.toLocaleString?.() ??
                                      '—'}
                                  </strong>

                                </div>


                                <div className="bucket-bar">

                                  <div
                                    style={{
                                      width: `${Math.min(
                                        Math.max(
                                          result?.positive_return_pct ||
                                          0,
                                          0
                                        ),
                                        100
                                      )}%`,
                                    }}
                                  />

                                </div>


                                <span className="bucket-result">

                                  {result?.average_return != null
                                    ? `${result.average_return.toFixed(2)}% avg`
                                    : '—'}

                                </span>

                              </div>

                            )
                          }
                        )}

                      </div>

                    </div>

                  )
                }
              )}


              {Object.keys(byFeature).length === 0 && (

                <div className="empty-analysis">

                  Feature analysis is not available
                  for this research run.

                </div>

              )}

            </div>

          </div>

        )}


        {/* =================================================
            MARKET REGIME ANALYSIS
            ================================================= */}

        {activeAnalysisTab === 'regime' && (

          <div className="analysis-panel">

            <div className="analysis-panel-top">

              <div>

                <span className="panel-kicker">
                  MARKET CONTEXT
                </span>

                <h4>
                  Performance by Market Regime
                </h4>

              </div>

              <div className="regime-definition">
                20D NIFTY 50 TRAILING RETURN
              </div>

            </div>


            <div className="regime-grid">

              {Object.entries(
                byMarketRegime
              ).map(
                ([regime, data]) => {

                  const metrics =
                    data?.performance?.[`T+${primaryAnalysisHorizon}`]

                  return (

                    <div
                      className={`regime-card regime-${regime.toLowerCase()}`}
                      key={regime}
                    >

                      <div className="regime-card-header">

                        <div className="regime-orb"></div>

                        <div>

                          <span className="regime-name">
                            {regime}
                          </span>

                          <small>
                            Market environment
                          </small>

                        </div>

                      </div>


                      <div className="regime-main-metric">

                        <span>
                          Average Return
                        </span>

                        <strong>

                          {metrics?.average_return != null
                            ? `${metrics.average_return.toFixed(2)}%`
                            : '—'}

                        </strong>

                      </div>


                      <div className="regime-stats">

                        <div>

                          <span>
                            Signals
                          </span>

                          <strong>
                            {data?.signal_count?.toLocaleString?.() ??
                              '—'}
                          </strong>

                        </div>


                        <div>

                          <span>
                            Positive
                          </span>

                          <strong>

                            {metrics?.positive_return_pct != null
                              ? `${metrics.positive_return_pct.toFixed(1)}%`
                              : '—'}

                          </strong>

                        </div>

                      </div>

                    </div>

                  )
                }
              )}


              {Object.keys(
                byMarketRegime
              ).length === 0 && (

                  <div className="empty-analysis">

                    Market-regime analysis is not
                    available for this research run.

                  </div>

                )}

            </div>

          </div>

        )}

      </div>


      {/* =====================================================
          WARNINGS
          ===================================================== */}

      {diagnostics.warnings?.length > 0 && (

        <div className="warnings-card">

          <div className="card-title">
            Research Warnings
          </div>

          {diagnostics.warnings.map(
            (warning, index) => (

              <div
                className="warning-row"
                key={index}
              >

                ⚠ {
                  typeof warning === 'string'
                    ? warning
                    : warning?.message ??
                    JSON.stringify(warning)
                }

              </div>

            )
          )}

        </div>

      )}


      {/* =====================================================
          RAW RESPONSE
          ===================================================== */}

      <details
        className="raw-result"
        onToggle={(event) => {
          setShowRawResponse(
            event.currentTarget.open
          )
        }}
      >

        <summary>
          View Raw Research Response
        </summary>

        {showRawResponse && (
          <pre>
            {rawResponse}
          </pre>
        )}

      </details>

    </div>
  )
}

export default ResearchResults