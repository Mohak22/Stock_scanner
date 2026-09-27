import { useEffect, useRef, useState } from 'react'
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
  const [jobId, setJobId] = useState(null)
  const [jobProgress, setJobProgress] = useState(0)
  const [jobStage, setJobStage] = useState('')
  const [jobStatus, setJobStatus] = useState(null)
  const [researchQuestion, setResearchQuestion] = useState(
    'Find oversold stocks using RSI and evaluate their forward returns.'
  )

  const [universe, setUniverse] = useState({
    type: 'all_stocks',
    value: '',
    symbols: [],
  })
  const [trainingStart, setTrainingStart] =
    useState('2016-01-01')

  const [trainingEnd, setTrainingEnd] =
    useState('2022-12-31')

  const [validationStart, setValidationStart] =
    useState('2023-01-01')

  const [validationEnd, setValidationEnd] =
    useState('2024-12-31')

  const [testingStart, setTestingStart] =
    useState('2025-01-01')

  const [testingEnd, setTestingEnd] =
    useState('2026-12-31')

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

  const eventSourceRef = useRef(null)

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

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
    }
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

    switch (featureId) {
      case 'rsi':
        defaultValue = 30
        break

      case 'volume':
      case 'delivery_quantity':
        defaultValue = 100000
        break

      case 'delivery_percentage':
        defaultValue = 50
        break

      case 'return':
        defaultValue = 0
        break

      default:
        defaultValue = 0
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

      validation_start:
        validationStart || null,

      validation_end:
        validationEnd || null,

      testing_start:
        testingStart || null,

      testing_end:
        testingEnd || null,

      universe,

      features: configuredFeatures,

      entry_conditions: conditions.map((condition) => {
        const numericValue = Number(condition.value)

        return {
          feature: condition.feature,

          ...(condition.period !== undefined &&
            condition.period !== null &&
            condition.period !== ''
            ? {
              period: Number(condition.period),
            }
            : {}),

          operator: condition.operator,

          value:
            condition.value !== '' &&
              !Number.isNaN(numericValue)
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
      return 'Please select the training period.'
    }

    if (trainingStart >= trainingEnd) {
      return 'Training start date must be before the training end date.'
    }

    if (!validationStart || !validationEnd) {
      return 'Please select the validation period.'
    }

    if (validationStart >= validationEnd) {
      return 'Validation start date must be before the validation end date.'
    }

    if (!testingStart || !testingEnd) {
      return 'Please select the testing period.'
    }

    if (testingStart >= testingEnd) {
      return 'Testing start date must be before the testing end date.'
    }

    if (trainingEnd >= validationStart) {
      return 'Training must finish before validation begins.'
    }

    if (validationEnd >= testingStart) {
      return 'Validation must finish before testing begins.'
    }

    if (conditions.length === 0) {
      return 'Add at least one research condition.'
    }

    if (evaluationHorizons.length === 0) {
      return 'Select at least one evaluation horizon.'
    }

    if (
      universe.type !== 'all_stocks' &&
      universe.type !== 'symbols' &&
      !universe.value
    ) {
      throw new Error('Please select a universe filter value.')
    }

    if (
      universe.type === 'symbols' &&
      (!universe.symbols || universe.symbols.length === 0)
    ) {
      throw new Error('Please enter at least one symbol.')
    }

    for (const condition of conditions) {
      if (!condition.feature) {
        return 'Every condition must have a feature.'
      }

      if (!condition.operator) {
        return 'Every condition must have an operator.'
      }

      if (!Number.isFinite(Number(condition.value))) {
        return 'Every condition value must be a valid number.'
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
    if (isRunning) {
      return
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }

    setRunError('')
    setResearchResult(null)

    setJobId(null)
    setJobProgress(0)
    setJobStage('')
    setJobStatus(null)

    let validationError

    try {
      validationError = validateResearch()
    } catch (error) {
      setRunError(
        error.message ||
        'Invalid research configuration.'
      )
      return
    }

    if (validationError) {
      setRunError(validationError)
      return
    }

    setIsRunning(true)

    try {
      const response = await fetch(
        `${API_BASE_URL}/research/run`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(
            buildResearchRequest()
          ),
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail ||
          'Failed to start research.'
        )
      }

      const newJobId = data.job_id

      if (!newJobId) {
        throw new Error(
          'Research job ID was not returned by the backend.'
        )
      }

      setJobId(newJobId)
      setJobStatus(data.status)
      setJobProgress(data.progress ?? 0)
      setJobStage(
        data.stage || 'Queued'
      )

      const eventSource = new EventSource(
        `${API_BASE_URL}/research/jobs/${newJobId}/stream`
      )

      eventSourceRef.current = eventSource

      eventSource.addEventListener(
        'progress',
        async (event) => {
          try {
            const job = JSON.parse(event.data)

            setJobStatus(job.status)
            setJobProgress(job.progress ?? 0)
            setJobStage(
              job.stage || ''
            )

            if (job.status === 'COMPLETED') {

              eventSource.close()

              if (
                eventSourceRef.current === eventSource
              ) {
                eventSourceRef.current = null
              }

              try {
                const resultResponse =
                  await fetch(
                    `${API_BASE_URL}/research/jobs/${newJobId}`
                  )

                const resultData =
                  await resultResponse.json()

                if (!resultResponse.ok) {
                  throw new Error(
                    resultData.detail ||
                    'Failed to retrieve research result.'
                  )
                }

                setResearchResult(
                  resultData.result
                )

              } catch (error) {

                setRunError(
                  error.message ||
                  'Failed to retrieve research result.'
                )

              } finally {

                setIsRunning(false)
              }
            }

            if (job.status === 'FAILED') {

              eventSource.close()

              if (
                eventSourceRef.current === eventSource
              ) {
                eventSourceRef.current = null
              }

              setRunError(
                job.error ||
                'Research execution failed.'
              )

              setIsRunning(false)
            }

          } catch (error) {

            eventSource.close()

            if (
              eventSourceRef.current === eventSource
            ) {
              eventSourceRef.current = null
            }

            setRunError(
              'Received an invalid progress update from the research server.'
            )

            setIsRunning(false)
          }
        }
      )

      eventSource.onerror = () => {

        eventSource.close()

        if (
          eventSourceRef.current === eventSource
        ) {
          eventSourceRef.current = null
        }

        setRunError(
          'Research progress connection was interrupted.'
        )

        setIsRunning(false)
      }

    } catch (error) {

      setRunError(
        error.message ||
        'Failed to start research.'
      )

      setIsRunning(false)
    }
  }

  const saveExperiment = async (result) => {
    const response = await fetch(
      `${API_BASE_URL}/research/experiments`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          research_result: result,

          name:
            researchQuestion.trim() ||
            'Untitled Research Experiment',

          notes:
            'Saved from Research Cockpit.',

          tags: [
            ...new Set(
              conditions
                .map((condition) =>
                  String(
                    condition.feature || ''
                  ).toUpperCase()
                )
                .filter(Boolean)
            ),
          ],
        }),
      }
    )

    const data = await response.json()

    if (!response.ok) {
      throw new Error(
        data.detail ||
        'Failed to save experiment.'
      )
    }

    return data
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
          trainingStart={trainingStart}
          trainingEnd={trainingEnd}
          validationStart={validationStart}
          validationEnd={validationEnd}
          testingStart={testingStart}
          testingEnd={testingEnd}
          onTrainingStartChange={setTrainingStart}
          onTrainingEndChange={setTrainingEnd}
          onValidationStartChange={setValidationStart}
          onValidationEndChange={setValidationEnd}
          onTestingStartChange={setTestingStart}
          onTestingEndChange={setTestingEnd}
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
        disabled={isRunning}
      />

      <ResearchExecution
        isRunning={isRunning}
        runError={runError}
        onRunResearch={runResearch}
        jobProgress={jobProgress}
        jobStage={jobStage}
        jobStatus={jobStatus}
      />

      <ResearchResults
        researchResult={researchResult}
        onSaveExperiment={saveExperiment}
      />
    </section>
  )
}

export default ResearchConfig
