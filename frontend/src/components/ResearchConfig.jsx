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

    const diagnostics = researchResult.diagnostics
    const performance = researchResult.performance

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
              {diagnostics?.signal_count ?? '—'}
            </strong>
          </div>

          <div className="result-card">
            <span>Signal Rate</span>
            <strong>
              {diagnostics?.signal_rate != null
                ? `${Number(diagnostics.signal_rate).toFixed(2)}%`
                : '—'}
            </strong>
          </div>

          <div className="result-card">
            <span>Stocks With Signals</span>
            <strong>
              {diagnostics?.stocks_with_signals ?? '—'}
            </strong>
          </div>

          <div className="result-card">
            <span>Sample Quality</span>
            <strong>
              {diagnostics?.sample_quality ?? '—'}
            </strong>
          </div>

        </div>

        {performance && (
          <div className="performance-card">
            <div className="card-title">
              Performance
            </div>

            <pre>
              {JSON.stringify(performance, null, 2)}
            </pre>
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