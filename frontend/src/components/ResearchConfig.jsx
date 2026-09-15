import { useEffect, useState } from 'react'
import { getFeatures } from '../api/researchApi'

const API_BASE_URL = 'http://127.0.0.1:8000'

function ResearchConfig() {
  const [features, setFeatures] = useState([])
  const [loadingFeatures, setLoadingFeatures] = useState(true)
  const [featureError, setFeatureError] = useState('')

  const [researchQuestion, setResearchQuestion] = useState(
    'Find oversold stocks using RSI and evaluate their forward returns.'
  )

  const [universe, setUniverse] = useState('all_stocks')

  const [trainingStart, setTrainingStart] = useState('2023-01-01')
  const [trainingEnd, setTrainingEnd] = useState('2025-12-31')

  const [conditions, setConditions] = useState([
    {
      id: 1,
      feature: 'rsi',
      period: 14,
      operator: '<',
      value: 30,
    },
  ])

  const [evaluationHorizons, setEvaluationHorizons] = useState([
    1,
    3,
    5,
    10,
  ])

  const [isRunning, setIsRunning] = useState(false)
  const [runError, setRunError] = useState('')
  const [researchResult, setResearchResult] = useState(null)
  const [activeAnalysisTab, setActiveAnalysisTab] = useState('stock')
  useEffect(() => {
    async function loadFeatures() {
      try {
        const data = await getFeatures()
        setFeatures(data.features)
      } catch (error) {
        setFeatureError(error.message)
      } finally {
        setLoadingFeatures(false)
      }
    }

    loadFeatures()
  }, [])

  const getFeatureDefinition = (featureId) => {
    return features.find((feature) => feature.id === featureId)
  }

  const addCondition = () => {
    setConditions([
      ...conditions,
      {
        id: Date.now(),
        feature: 'rsi',
        period: 14,
        operator: '<',
        value: 30,
      },
    ])
  }

  const removeCondition = (id) => {
    setConditions(
      conditions.filter((condition) => condition.id !== id)
    )
  }

  const updateCondition = (id, field, value) => {
    setConditions(
      conditions.map((condition) =>
        condition.id === id
          ? { ...condition, [field]: value }
          : condition
      )
    )
  }

  const updateFeature = (id, featureId) => {
    const selectedFeature = getFeatureDefinition(featureId)

    const parameter = selectedFeature?.parameters?.[0]

    let defaultValue = 0

    if (featureId === 'rsi') {
      defaultValue = 30
    } else if (
      featureId === 'volume' ||
      featureId === 'delivery_quantity'
    ) {
      defaultValue = 100000
    }

    setConditions(
      conditions.map((condition) => {
        if (condition.id !== id) {
          return condition
        }

        return {
          ...condition,
          feature: featureId,
          period: parameter?.default ?? undefined,
          value: defaultValue,
        }
      })
    )
  }

  const toggleHorizon = (horizon) => {
    if (evaluationHorizons.includes(horizon)) {
      if (evaluationHorizons.length === 1) {
        return
      }

      setEvaluationHorizons(
        evaluationHorizons.filter((item) => item !== horizon)
      )

      return
    }

    setEvaluationHorizons(
      [...evaluationHorizons, horizon].sort((a, b) => a - b)
    )
  }

  const buildResearchRequest = () => {
    const configuredFeatures = []

    conditions.forEach((condition) => {
      const alreadyExists = configuredFeatures.some(
        (feature) =>
          feature.type === condition.feature &&
          feature.period === condition.period
      )

      if (!alreadyExists) {
        configuredFeatures.push({
          type: condition.feature,
          ...(condition.period !== undefined &&
            condition.period !== null
            ? { period: condition.period }
            : {}),
        })
      }
    })

    return {
      training_start: trainingStart,
      training_end: trainingEnd,

      universe: {
        type: universe,
        symbols: [],
      },

      features: configuredFeatures,

      entry_conditions: conditions.map((condition) => {
        const numericValue = Number(condition.value)

        return {
          feature: condition.feature,

          ...(condition.period !== undefined &&
            condition.period !== null &&
            condition.period !== ''
            ? { period: Number(condition.period) }
            : {}),

          operator: condition.operator,

          value:
            condition.value !== '' && !Number.isNaN(numericValue)
              ? numericValue
              : condition.value,
        }
      }),

      evaluation_horizons: evaluationHorizons,
    }
  }

  const validateResearch = () => {
    if (!researchQuestion.trim()) {
      return 'Please define a research question.'
    }

    if (!trainingStart || !trainingEnd) {
      return 'Please select a research period.'
    }

    if (trainingStart >= trainingEnd) {
      return 'Training start date must be before the training end date.'
    }

    if (conditions.length === 0) {
      return 'Add at least one research condition.'
    }

    if (evaluationHorizons.length === 0) {
      return 'Select at least one evaluation horizon.'
    }

    for (const condition of conditions) {
      if (!condition.feature) {
        return 'Every condition must have a feature.'
      }

      if (!condition.operator) {
        return 'Every condition must have an operator.'
      }

      if (
        condition.value === '' ||
        condition.value === null ||
        condition.value === undefined
      ) {
        return 'Every condition must have a value.'
      }
    }

    return null
  }

  const runResearch = async () => {
    setRunError('')
    setResearchResult(null)

    const validationError = validateResearch()

    if (validationError) {
      setRunError(validationError)
      return
    }

    const requestBody = buildResearchRequest()

    setIsRunning(true)

    try {
      const response = await fetch(`${API_BASE_URL}/research/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      const data = await response.json()

      if (!response.ok) {
        const message =
          data?.detail || 'Research execution failed.'

        throw new Error(
          Array.isArray(message)
            ? message.map((item) => item.msg).join(', ')
            : message
        )
      }

      setResearchResult(data)
    } catch (error) {
      setRunError(error.message)
    } finally {
      setIsRunning(false)
    }
  }

  const renderResultSummary = () => {
    if (!researchResult) {
      return null
    }

    const training = researchResult.training || {}
    const summary = training.summary || {}
    const diagnostics = training.diagnostics || {}
    const performance = training.performance || {}
    const analysis = training.analysis || {}

    return (
      <div className="research-results">

        <div className="results-header">
          <div>
            <span className="section-kicker">
              RESEARCH OUTPUT
            </span>

            <h2>Research Completed</h2>

            <p>
              The backend successfully executed the configured research
              experiment.
            </p>
          </div>

          <div className="research-status success">
            <span className="status-dot"></span>
            COMPLETE
          </div>
        </div>

        <div className="results-grid">

          <div className="result-card">
            <span>Signals</span>
            <strong>
              {summary?.signal_count?.toLocaleString() ?? '—'}
            </strong>
          </div>

          <div className="result-card">
            <span>Signal Rate</span>
            <strong>
              {summary?.signal_rate != null
                ? `${Number(summary.signal_rate).toFixed(2)}%`
                : '—'}
            </strong>
          </div>

          <div className="result-card">
            <span>Stocks With Signals</span>
            <strong>
              {summary?.stocks_with_signals?.toLocaleString() ?? '—'}
            </strong>
          </div>

          <div className="result-card">
            <span>Sample Quality</span>
            <strong>
              {diagnostics?.sample_quality?.classification ?? '—'}
            </strong>
          </div>

        </div>

        {performance && (
          <div className="performance-card">
            <div className="card-title">
              Performance
            </div>

            <div className="result-section">
              <div className="section-heading">
                <div>
                  <span className="section-kicker">PERFORMANCE ANALYSIS</span>
                  <h3>Forward Return Performance</h3>
                </div>

                <span className="section-meta">
                  {Object.keys(performance || {}).length} horizons evaluated
                </span>
              </div>

              <div className="performance-grid">
                {Object.entries(performance || {}).map(([horizon, metrics]) => (
                  <div className="performance-card" key={horizon}>
                    <div className="performance-card-header">
                      <span className="horizon-label">{horizon}</span>
                      <span className="observation-count">
                        {metrics.observations?.toLocaleString()} observations
                      </span>
                    </div>

                    <div className="primary-performance">
                      <span>Average Return</span>
                      <strong
                        className={
                          metrics.average_return >= 0
                            ? "positive-value"
                            : "negative-value"
                        }
                      >
                        {metrics.average_return?.toFixed(2)}%
                      </strong>
                    </div>

                    <div className="performance-metrics">
                      <div>
                        <span>Median</span>
                        <strong>{metrics.median_return?.toFixed(2)}%</strong>
                      </div>

                      <div>
                        <span>Positive</span>
                        <strong>{metrics.positive_return_pct?.toFixed(2)}%</strong>
                      </div>

                      <div>
                        <span>Excess vs NIFTY</span>
                        <strong
                          className={
                            metrics.average_excess_return >= 0
                              ? "positive-value"
                              : "negative-value"
                          }
                        >
                          {metrics.average_excess_return?.toFixed(2)}%
                        </strong>
                      </div>

                      <div>
                        <span>Outperformed</span>
                        <strong>{metrics.outperformed_market_pct?.toFixed(2)}%</strong>
                      </div>

                      <div>
                        <span>Best</span>
                        <strong className="positive-value">
                          {metrics.best_return?.toFixed(2)}%
                        </strong>
                      </div>

                      <div>
                        <span>Worst</span>
                        <strong className="negative-value">
                          {metrics.worst_return?.toFixed(2)}%
                        </strong>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="performance-table-wrapper">
                <table className="performance-table">
                  <thead>
                    <tr>
                      <th>Horizon</th>
                      <th>Avg Return</th>
                      <th>Median</th>
                      <th>Positive</th>
                      <th>Avg NIFTY</th>
                      <th>Excess Return</th>
                      <th>Outperformed</th>
                    </tr>
                  </thead>

                  <tbody>
                    {Object.entries(performance || {}).map(([horizon, metrics]) => (
                      <tr key={horizon}>
                        <td className="table-horizon">{horizon}</td>

                        <td
                          className={
                            metrics.average_return >= 0
                              ? "positive-value"
                              : "negative-value"
                          }
                        >
                          {metrics.average_return?.toFixed(2)}%
                        </td>

                        <td>{metrics.median_return?.toFixed(2)}%</td>

                        <td>{metrics.positive_return_pct?.toFixed(2)}%</td>

                        <td>{metrics.average_market_return?.toFixed(2)}%</td>

                        <td
                          className={
                            metrics.average_excess_return >= 0
                              ? "positive-value"
                              : "negative-value"
                          }
                        >
                          {metrics.average_excess_return?.toFixed(2)}%
                        </td>

                        <td>{metrics.outperformed_market_pct?.toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="analysis-section">
              <div className="analysis-header">
                <div>
                  <span className="section-kicker">RESEARCH INTELLIGENCE</span>
                  <h3>Signal Analysis</h3>
                  <p>
                    Decompose the research result across stocks, features and market regimes.
                  </p>
                </div>

                <div className="analysis-live-indicator">
                  <span className="analysis-pulse"></span>
                  ANALYSIS READY
                </div>
              </div>

              <div className="analysis-tabs">
                <button
                  className={`analysis-tab ${activeAnalysisTab === "stock" ? "active" : ""
                    }`}
                  onClick={() => setActiveAnalysisTab("stock")}
                >
                  <span className="tab-number">01</span>
                  <span>
                    <strong>By Stock</strong>
                    <small>Stock-level behaviour</small>
                  </span>
                </button>

                <button
                  className={`analysis-tab ${activeAnalysisTab === "feature" ? "active" : ""
                    }`}
                  onClick={() => setActiveAnalysisTab("feature")}
                >
                  <span className="tab-number">02</span>
                  <span>
                    <strong>By Feature</strong>
                    <small>Feature effectiveness</small>
                  </span>
                </button>

                <button
                  className={`analysis-tab ${activeAnalysisTab === "regime" ? "active" : ""
                    }`}
                  onClick={() => setActiveAnalysisTab("regime")}
                >
                  <span className="tab-number">03</span>
                  <span>
                    <strong>Market Regime</strong>
                    <small>Contextual behaviour</small>
                  </span>
                </button>
              </div>

              {activeAnalysisTab === "stock" && (
                <div className="analysis-panel">
                  <div className="analysis-panel-top">
                    <div>
                      <span className="panel-kicker">STOCK ATTRIBUTION</span>
                      <h4>Performance by Stock</h4>
                    </div>

                    <div className="stock-analysis-summary">
                      <span>
                        {Object.keys(analysis?.by_stock || {}).length}
                      </span>
                      stocks analysed
                    </div>
                  </div>

                  <div className="stock-table-wrapper">
                    <table className="stock-analysis-table">
                      <thead>
                        <tr>
                          <th>Stock</th>
                          <th>Signals</th>
                          <th>T+1</th>
                          <th>T+3</th>
                          <th>T+5</th>
                          <th>T+10</th>
                        </tr>
                      </thead>

                      <tbody>
                        {Object.entries(analysis?.by_stock || {})
                          .slice(0, 100)
                          .map(([symbol, stock]) => (
                            <tr key={symbol}>
                              <td>
                                <div className="stock-symbol">
                                  <span className="stock-icon">◈</span>
                                  <strong>{symbol}</strong>
                                </div>
                              </td>

                              <td className="signal-count">
                                {stock.signal_count?.toLocaleString()}
                              </td>

                              {[1, 3, 5, 10].map((horizon) => {
                                const metrics = stock.performance?.[`T+${horizon}`]

                                return (
                                  <td
                                    key={horizon}
                                    className={
                                      metrics?.average_return >= 0
                                        ? "positive-value"
                                        : "negative-value"
                                    }
                                  >
                                    {metrics?.average_return != null
                                      ? `${metrics.average_return.toFixed(2)}%`
                                      : "—"}
                                  </td>
                                )
                              })}
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>

                  {Object.keys(analysis?.by_stock || {}).length > 100 && (
                    <div className="table-footer">
                      Showing first 100 stocks from{" "}
                      {Object.keys(analysis.by_stock).length.toLocaleString()} analysed.
                    </div>
                  )}
                </div>
              )}

              {activeAnalysisTab === "feature" && (
                <div className="analysis-panel">
                  <div className="analysis-panel-top">
                    <div>
                      <span className="panel-kicker">FEATURE ATTRIBUTION</span>
                      <h4>Performance by Feature</h4>
                    </div>

                    <div className="feature-intelligence">
                      FEATURE → OUTCOME
                    </div>
                  </div>

                  <div className="feature-analysis-grid">
                    {Object.entries(analysis?.by_feature || {}).map(
                      ([feature, data]) => (
                        <div className="feature-analysis-card" key={feature}>
                          <div className="feature-card-top">
                            <div className="feature-symbol">ƒx</div>

                            <div>
                              <strong>{feature}</strong>
                              <span>Observed signal distribution</span>
                            </div>
                          </div>

                          <div className="feature-card-body">
                            {Object.entries(data || {}).map(([bucket, bucketData]) => (
                              <div className="feature-bucket" key={bucket}>
                                <div className="bucket-label">
                                  <span>{bucket}</span>
                                  <strong>
                                    {bucketData?.signal_count?.toLocaleString?.() ?? "—"}
                                  </strong>
                                </div>

                                <div className="bucket-bar">
                                  <div
                                    style={{
                                      width: `${Math.min(
                                        Math.max(
                                          bucketData?.positive_return_pct || 0,
                                          0
                                        ),
                                        100
                                      )}%`,
                                    }}
                                  />
                                </div>

                                <span className="bucket-result">
                                  {bucketData?.average_return != null
                                    ? `${bucketData.average_return.toFixed(2)}% avg`
                                    : "—"}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )
                    )}

                    {Object.keys(analysis?.by_feature || {}).length === 0 && (
                      <div className="empty-analysis">
                        Feature analysis is not available for this research run.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeAnalysisTab === "regime" && (
                <div className="analysis-panel">
                  <div className="analysis-panel-top">
                    <div>
                      <span className="panel-kicker">MARKET CONTEXT</span>
                      <h4>Performance by Market Regime</h4>
                    </div>

                    <div className="regime-definition">
                      20D NIFTY 50 TRAILING RETURN
                    </div>
                  </div>

                  <div className="regime-grid">
                    {Object.entries(analysis?.by_market_regime || {}).map(
                      ([regime, data]) => (
                        <div
                          className={`regime-card regime-${regime.toLowerCase()}`}
                          key={regime}
                        >
                          <div className="regime-card-header">
                            <div className="regime-orb"></div>

                            <div>
                              <span className="regime-name">{regime}</span>
                              <small>Market environment</small>
                            </div>
                          </div>

                          <div className="regime-main-metric">
                            <span>Average Return</span>
                            <strong>
                              {data?.performance?.T5?.average_return != null
                                ? `${data.performance.T5.average_return.toFixed(2)}%`
                                : data?.performance?.["T+5"]?.average_return != null
                                  ? `${data.performance["T+5"].average_return.toFixed(2)}%`
                                  : "—"}
                            </strong>
                          </div>

                          <div className="regime-stats">
                            <div>
                              <span>Signals</span>
                              <strong>
                                {data?.signal_count?.toLocaleString?.() ?? "—"}
                              </strong>
                            </div>

                            <div>
                              <span>Positive</span>
                              <strong>
                                {data?.performance?.["T+5"]?.positive_return_pct != null
                                  ? `${data.performance["T+5"].positive_return_pct.toFixed(
                                    1
                                  )}%`
                                  : "—"}
                              </strong>
                            </div>
                          </div>
                        </div>
                      )
                    )}

                    {Object.keys(analysis?.by_market_regime || {}).length === 0 && (
                      <div className="empty-analysis">
                        Market-regime analysis is not available for this research run.
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {diagnostics?.warnings?.length > 0 && (
          <div className="warnings-card">
            <div className="card-title">
              Research Warnings
            </div>

            {diagnostics.warnings.map((warning, index) => (
              <div
                className="warning-row"
                key={index}
              >
                ⚠ {warning}
              </div>
            ))}
          </div>
        )}

        <details className="raw-result">
          <summary>
            View Raw Research Response
          </summary>

          <pre>
            {JSON.stringify(researchResult, null, 2)}
          </pre>
        </details>

      </div>
    )
  }

  return (
    <section className="research-config">

      <div className="section-header">

        <div>
          <span className="section-kicker">
            RESEARCH CONFIGURATION
          </span>

          <h2>Define Your Research Question</h2>

          <p>
            Build a hypothesis using historical market data and test its
            behaviour across different market conditions.
          </p>

          {loadingFeatures && (
            <p className="backend-status">
              Loading research features...
            </p>
          )}

          {featureError && (
            <p className="backend-error">
              {featureError}
            </p>
          )}

          {!loadingFeatures && !featureError && (
            <p className="backend-status">
              {features.length} research features available
            </p>
          )}
        </div>

        <div className="research-status">
          <span className="status-dot"></span>
          {isRunning ? 'RUNNING' : 'READY'}
        </div>

      </div>


      <div className="research-question">

        <label>
          Research Question
        </label>

        <input
          type="text"
          value={researchQuestion}
          onChange={(event) =>
            setResearchQuestion(event.target.value)
          }
          placeholder="Example: Find stocks that are oversold but showing signs of accumulation..."
        />

      </div>


      <div className="config-grid">

        <div className="config-card">

          <label>
            Universe
          </label>

          <select
            value={universe}
            onChange={(event) =>
              setUniverse(event.target.value)
            }
          >
            <option value="all_stocks">
              All Stocks
            </option>

            <option value="symbols" disabled>
              Custom Symbols — backend support later
            </option>
          </select>

          <span className="field-help">
            Select the stocks that should participate in the research.
          </span>

        </div>


        <div className="config-card">

          <label>
            Research Period
          </label>

          <div className="date-inputs">

            <input
              type="date"
              value={trainingStart}
              onChange={(event) =>
                setTrainingStart(event.target.value)
              }
            />

            <span>→</span>

            <input
              type="date"
              value={trainingEnd}
              onChange={(event) =>
                setTrainingEnd(event.target.value)
              }
            />

          </div>

          <span className="field-help">
            Historical period used for signal generation and evaluation.
          </span>

        </div>

      </div>


      <div className="conditions-section">

        <div className="conditions-header">

          <div>
            <label>
              Research Conditions
            </label>

            <span>
              Combine technical and market features to define your hypothesis.
            </span>
          </div>

          <button
            className="secondary-button"
            onClick={addCondition}
            disabled={isRunning}
          >
            + Add Condition
          </button>

        </div>


        {conditions.map((condition) => {

          const featureDefinition =
            getFeatureDefinition(condition.feature)

          const hasParameter =
            featureDefinition?.parameters?.length > 0

          return (
            <div
              className="condition-row"
              key={condition.id}
            >

              <select
                value={condition.feature}
                onChange={(event) =>
                  updateFeature(
                    condition.id,
                    event.target.value
                  )
                }
                disabled={isRunning}
              >

                {features.map((feature) => (
                  <option
                    key={feature.id}
                    value={feature.id}
                  >
                    {feature.name}
                  </option>
                ))}

              </select>


              {hasParameter && (
                <input
                  type="number"
                  min={
                    featureDefinition.parameters[0].minimum
                  }
                  max={
                    featureDefinition.parameters[0].maximum
                  }
                  value={condition.period ?? ''}
                  onChange={(event) =>
                    updateCondition(
                      condition.id,
                      'period',
                      Number(event.target.value)
                    )
                  }
                  disabled={isRunning}
                />
              )}


              <select
                value={condition.operator}
                onChange={(event) =>
                  updateCondition(
                    condition.id,
                    'operator',
                    event.target.value
                  )
                }
                disabled={isRunning}
              >

                <option value="<">
                  &lt;
                </option>

                <option value="<=">
                  &lt;=
                </option>

                <option value=">">
                  &gt;
                </option>

                <option value=">=">
                  &gt;=
                </option>

                <option value="==">
                  ==
                </option>

                <option value="!=">
                  !=
                </option>

              </select>


              <input
                type="number"
                value={condition.value}
                onChange={(event) =>
                  updateCondition(
                    condition.id,
                    'value',
                    event.target.value
                  )
                }
                disabled={isRunning}
              />


              <button
                className="remove-condition"
                onClick={() =>
                  removeCondition(condition.id)
                }
                disabled={
                  isRunning || conditions.length === 1
                }
              >
                ×
              </button>

            </div>
          )
        })}

      </div>


      <div className="horizons-section">

        <div>
          <label>
            Evaluation Horizons
          </label>

          <span>
            Forward-return periods calculated by the research engine.
          </span>
        </div>

        <div className="horizon-options">

          {[1, 3, 5, 10].map((horizon) => (
            <button
              key={horizon}
              className={
                evaluationHorizons.includes(horizon)
                  ? 'horizon-button selected'
                  : 'horizon-button'
              }
              onClick={() =>
                toggleHorizon(horizon)
              }
              disabled={isRunning}
            >
              T+{horizon}
            </button>
          ))}

        </div>

      </div>


      {runError && (
        <div className="run-error">
          <strong>Research could not be executed</strong>
          <span>{runError}</span>
        </div>
      )}


      <div className="run-section">

        <div>
          <strong>
            {isRunning
              ? 'Running your research...'
              : 'Ready to test your hypothesis?'}
          </strong>

          <span>
            {isRunning
              ? 'The backend research engine is processing your configuration.'
              : 'Running research does not save an experiment automatically.'}
          </span>
        </div>

        <button
          className="run-button"
          onClick={runResearch}
          disabled={isRunning || loadingFeatures}
        >
          {isRunning
            ? 'RUNNING...'
            : 'RUN RESEARCH'}
        </button>

      </div>


      {renderResultSummary()}

    </section>
  )
}

export default ResearchConfig