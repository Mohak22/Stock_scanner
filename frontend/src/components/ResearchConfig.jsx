import { useEffect, useState } from 'react'
import { getFeatures } from '../api/researchApi'
import ResearchQuestion from './research/ResearchQuestion'
import UniverseConfig from './research/UniverseConfig'
import DateRangeConfig from './research/DateRangeConfig'
import ConditionBuilder from './research/ConditionBuilder'
import EvaluationHorizons from './research/EvaluationHorizons'
import ResearchExecution from './research/ResearchExecution'
import ResearchResults from './research/ResearchResults'

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

  const [evaluationHorizons, setEvaluationHorizons] = useState([1, 3, 5, 10])
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

  const getFeatureDefinition = (featureId) =>
    features.find((feature) => feature.id === featureId)

  const addCondition = () => {
    setConditions((current) => [
      ...current,
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
    setConditions((current) =>
      current.filter((condition) => condition.id !== id)
    )
  }

  const updateCondition = (id, field, value) => {
    setConditions((current) =>
      current.map((condition) =>
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

    setConditions((current) =>
      current.map((condition) => {
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
    setEvaluationHorizons((current) => {
      if (current.includes(horizon)) {
        if (current.length === 1) {
          return current
        }
        return current.filter((item) => item !== horizon)
      }

      return [...current, horizon].sort((a, b) => a - b)
    })
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
            condition.period !== null &&
            condition.period !== ''
            ? { period: Number(condition.period) }
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

      const featureDefinition = getFeatureDefinition(condition.feature)
      const parameter = featureDefinition?.parameters?.[0]

      if (parameter && condition.period !== '' && condition.period != null) {
        const period = Number(condition.period)

        if (!Number.isInteger(period)) {
          return `${featureDefinition.name} period must be a whole number.`
        }

        if (
          parameter.minimum != null &&
          period < parameter.minimum
        ) {
          return `${featureDefinition.name} period must be at least ${parameter.minimum}.`
        }

        if (
          parameter.maximum != null &&
          period > parameter.maximum
        ) {
          return `${featureDefinition.name} period must be at most ${parameter.maximum}.`
        }
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

    setIsRunning(true)

    try {
      const response = await fetch(`${API_BASE_URL}/research/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(buildResearchRequest()),
      })

      const data = await response.json()

      if (!response.ok) {
        const message = data?.detail || 'Research execution failed.'

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

  return (
    <section className="research-config">
      <div className="section-header">
        <div>
          <span className="section-kicker">RESEARCH CONFIGURATION</span>

          <h2>Define Your Research Question</h2>

          <p>
            Build a hypothesis using historical market data and test its
            behaviour across different market conditions.
          </p>

          {loadingFeatures && (
            <p className="backend-status">Loading research features...</p>
          )}

          {featureError && (
            <p className="backend-error">{featureError}</p>
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

      <ResearchQuestion
        value={researchQuestion}
        onChange={setResearchQuestion}
      />

      <div className="config-grid">
        <UniverseConfig
          value={universe}
          onChange={setUniverse}
          isRunning={isRunning}
        />

        <DateRangeConfig
          startDate={trainingStart}
          endDate={trainingEnd}
          onStartChange={setTrainingStart}
          onEndChange={setTrainingEnd}
          isRunning={isRunning}
        />
      </div>

      <ConditionBuilder
        conditions={conditions}
        features={features}
        isRunning={isRunning}
        onAddCondition={addCondition}
        onRemoveCondition={removeCondition}
        onUpdateCondition={updateCondition}
        onUpdateFeature={updateFeature}
      />

      <EvaluationHorizons
        horizons={[1, 3, 5, 10]}
        selectedHorizons={evaluationHorizons}
        onToggle={toggleHorizon}
        isRunning={isRunning}
      />

      <ResearchExecution
        isRunning={isRunning}
        runError={runError}
        onRunResearch={runResearch}
      />

      <ResearchResults researchResult={researchResult} />
    </section>
  )
}

export default ResearchConfig
