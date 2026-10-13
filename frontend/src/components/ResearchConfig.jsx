import { useEffect, useRef, useState } from 'react'
import { getFeatures } from '../api/researchApi'
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
  const [researchStage, setResearchStage] =
    useState('development')
  const [jobId, setJobId] = useState(null)
  const [jobProgress, setJobProgress] = useState(0)
  const [jobStage, setJobStage] = useState('')
  const [jobStatus, setJobStatus] = useState(null)

  const [universe, setUniverse] = useState({
    type: 'all_stocks',
    value: '',
    symbols: [],
  })

  const [developmentStart, setDevelopmentStart] =
    useState('2016-01-01')

  const [developmentEnd, setDevelopmentEnd] =
    useState('2022-12-31')

  const [validationStart, setValidationStart] =
    useState('2023-01-01')

  const [validationEnd, setValidationEnd] =
    useState('2024-12-31')

  const [holdoutStart, setHoldoutStart] =
    useState('2025-01-01')

  const [holdoutEnd, setHoldoutEnd] = useState('')

  const [conditions, setConditions] = useState([
    {
      id: 1,
      left: { feature: 'rsi', parameters: { period: 14 }, multiplier: 1 },
      operator: '<',
      right: { value: 30, multiplier: 1 },
    },
  ])

  const [evaluationHorizons, setEvaluationHorizons] =
    useState([1, 3, 5, 10])

  const [isRunning, setIsRunning] = useState(false)
  const [runError, setRunError] = useState('')
  const [researchResult, setResearchResult] = useState(null)

  const eventSourceRef = useRef(null)

  useEffect(() => {
    async function loadAvailableDates() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/data/dates`
        )

        const data = await response.json()

        if (!response.ok) {
          throw new Error(
            data.detail ||
            'Failed to load available market dates.'
          )
        }

        const dates = Array.isArray(data.available_dates)
          ? data.available_dates
          : []

        if (dates.length > 0) {
          setHoldoutEnd(
            String(dates[dates.length - 1]).slice(0, 10)
          )
        }
      } catch (error) {
        setFeatureError(
          error.message ||
          'Failed to load available market dates.'
        )
      }
    }

    loadAvailableDates()
  }, [])

  useEffect(() => {
    async function loadFeatures() {
      try {
        setFeatureError('')

        const data = await getFeatures()

        const availableFeatures =
          Array.isArray(data.features)
            ? data.features
            : []

        if (availableFeatures.length === 0) {
          throw new Error(
            'No research indicators are available.'
          )
        }

        setFeatures(availableFeatures)

        const firstFeature = availableFeatures[0]

        setConditions((current) =>
          current.map((condition) => {
            if (
              availableFeatures.some(
                (feature) =>
                  feature.id === condition.feature
              )
            ) {
              return condition
            }

            const parameter =
              firstFeature.parameters?.[0]

            return {
              ...condition,
              feature: firstFeature.id,
              period:
                parameter?.default ?? undefined,
            }
          })
        )
      } catch (error) {
        setFeatureError(
          error.message ||
          'Failed to load research indicators.'
        )
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

  const buildFeatureExpression = (featureId) => {
    const feature = getFeatureDefinition(featureId)
    return {
      feature: feature?.id || featureId || '',
      parameters: Object.fromEntries(
        (feature?.parameters || []).map((parameter) => [
          parameter.id,
          parameter.default ?? '',
        ])
      ),
      multiplier: 1,
    }
  }

  const setNestedValue = (object, path, value) => {
    const keys = path.split('.')
    const result = { ...object }
    let cursor = result
    for (let i = 0; i < keys.length - 1; i += 1) {
      cursor[keys[i]] = { ...(cursor[keys[i]] || {}) }
      cursor = cursor[keys[i]]
    }
    cursor[keys[keys.length - 1]] = value
    return result
  }

  const updateCondition = (id, path, value) => {
    setConditions((current) =>
      current.map((condition) =>
        condition.id === id ? setNestedValue(condition, path, value) : condition
      )
    )
  }

  const addCondition = () => {
    setConditions((current) => [
      ...current,
      {
        id: Date.now(),
        left: buildFeatureExpression(features[0]?.id || ''),
        operator: '<',
        right: { value: 0, multiplier: 1 },
      },
    ])
  }

  const removeCondition = (id) => {
    setConditions((current) =>
      current.filter((condition) => condition.id !== id)
    )
  }

  const updateFeature = (id, side, featureId) => {
    const expression = buildFeatureExpression(featureId)
    setConditions((current) =>
      current.map((condition) =>
        condition.id === id ? { ...condition, [side]: expression } : condition
      )
    )
  }


  const toggleHorizon = (horizon) => {
    setEvaluationHorizons((current) => {
      if (current.includes(horizon)) {
        if (current.length === 1) {
          return current
        }

        return current.filter(
          (item) => item !== horizon
        )
      }

      return [
        ...current,
        horizon,
      ].sort((a, b) => a - b)
    })
  }

  const buildResearchRequest = () => {
    const configuredFeatures = []
    const addFeature = (expression) => {
      if (!expression?.feature) return
      const config = {
        type: expression.feature,
        parameters: { ...(expression.parameters || {}) },
      }
      const key = JSON.stringify(config)
      if (!configuredFeatures.some((item) => JSON.stringify(item) === key)) {
        configuredFeatures.push(config)
      }
    }

    conditions.forEach((condition) => {
      addFeature(condition.left)
      addFeature(condition.right)
    })

    let activeStart = developmentStart
    let activeEnd = developmentEnd
    if (researchStage === 'validation') {
      activeStart = validationStart
      activeEnd = validationEnd
    }
    if (researchStage === 'testing') {
      activeStart = holdoutStart
      activeEnd = holdoutEnd
    }

    const expression = (item) =>
      item?.feature
        ? {
          feature: item.feature,
          parameters: { ...(item.parameters || {}) },
          ...(item.multiplier != null && item.multiplier !== '' && Number(item.multiplier) !== 1
            ? { multiplier: Number(item.multiplier) }
            : {}),
        }
        : {
          value: Number(item?.value),
          ...(item?.multiplier != null && item.multiplier !== '' && Number(item.multiplier) !== 1
            ? { multiplier: Number(item.multiplier) }
            : {}),
        }

    return {
      development_start: activeStart,
      development_end: activeEnd,
      validation_start: null,
      validation_end: null,
      holdout_start: null,
      holdout_end: null,
      universe,
      features: configuredFeatures,
      entry_conditions: conditions.map((condition) => ({
        left: expression(condition.left),
        operator: condition.operator,
        right: expression(condition.right),
      })),
      evaluation_horizons: evaluationHorizons,
      signal_timing: {
        observation: 'signal_date_close',
        entry: 'same_signal_date_close_proxy',
        price_basis: 'CLOSE',
      },
      outcome_definition: {
        anchor: 'signal_date',
        price_basis: 'CLOSE',
        horizons: evaluationHorizons,
      },
    }
  }


  const validateResearch = () => {
    let startDate = developmentStart
    let endDate = developmentEnd

    if (researchStage === 'validation') {
      startDate = validationStart
      endDate = validationEnd
    }

    if (researchStage === 'testing') {
      startDate = holdoutStart
      endDate = holdoutEnd
    }

    if (!startDate || !endDate) {
      return 'Please select the research period.'
    }

    if (startDate >= endDate) {
      return 'Research start date must be before the end date.'
    }

    if (conditions.length === 0) {
      return 'Add at least one research condition.'
    }

    if (evaluationHorizons.length === 0) {
      return 'Select at least one evaluation horizon.'
    }

    if (features.length === 0) {
      return 'Research indicators are still loading.'
    }

    if (
      universe.type !== 'all_stocks' &&
      universe.type !== 'symbols' &&
      universe.type !== 'major_stocks' &&
      !universe.value
    ) {
      return 'Please select a universe filter value.'
    }

    if (
      universe.type === 'symbols' &&
      (!universe.symbols ||
        universe.symbols.length === 0)
    ) {
      return 'Please enter at least one symbol.'
    }

    const validateMultiplier = (
      expression,
      label
    ) => {
      const multiplier =
        expression?.multiplier ?? 1

      if (
        multiplier === '' ||
        multiplier === null ||
        multiplier === undefined ||
        !Number.isFinite(
          Number(multiplier)
        ) ||
        Number(multiplier) < 0
      ) {
        return (
          `${label} must have a valid non-negative multiplier.`
        )
      }

      return null
    }

    const validateExpression = (
      expression,
      label,
      allowValue
    ) => {
      if (!expression) {
        return `${label} is required.`
      }

      /*
       * Canonical expression is either:
       *
       * {
       *   feature: 'rsi',
       *   parameters: { period: 14 },
       *   multiplier: 1
       * }
       *
       * OR
       *
       * {
       *   value: 30,
       *   multiplier: 1
       * }
       */

      if (!expression.feature) {
        if (!allowValue) {
          return `${label} must use a valid research indicator.`
        }

        const value = expression.value

        if (
          value === '' ||
          value === null ||
          value === undefined ||
          !Number.isFinite(
            Number(value)
          )
        ) {
          return (
            `${label} must have a valid numeric value.`
          )
        }

        return validateMultiplier(
          expression,
          label
        )
      }

      const definition =
        getFeatureDefinition(
          expression.feature
        )

      if (!definition) {
        return (
          `${label} must use a valid research indicator.`
        )
      }

      const parameters =
        expression.parameters || {}

      const parameterDefinitions =
        definition.parameters || []

      /*
       * Make sure the expression does not
       * contain parameters that the registry
       * does not understand.
       */
      const unknownParameters =
        Object.keys(
          parameters
        ).filter(
          (parameterId) =>
            !parameterDefinitions.some(
              (parameter) =>
                parameter.id ===
                parameterId
            )
        )

      if (
        unknownParameters.length > 0
      ) {
        return (
          `${label} contains unsupported parameter(s): ` +
          unknownParameters.join(', ')
        )
      }

      /*
       * Validate every parameter generically.
       *
       * This is intentionally NOT hardcoded
       * to "period".
       */
      for (
        const parameter of
        parameterDefinitions
      ) {
        const parameterId =
          parameter.id

        const value =
          parameters[
          parameterId
          ] ??
          parameter.default

        if (
          value === undefined ||
          value === null ||
          value === ''
        ) {
          if (
            parameter.required !==
            false
          ) {
            return (
              `${label} requires ${parameter.name}.`
            )
          }

          continue
        }

        const type =
          String(
            parameter.type || ''
          ).toLowerCase()

        if (
          type === 'integer'
        ) {
          if (
            !Number.isInteger(
              Number(value)
            )
          ) {
            return (
              `${label} ${parameter.name} must be a whole number.`
            )
          }
        }

        if (
          type === 'number' ||
          type === 'float'
        ) {
          if (
            !Number.isFinite(
              Number(value)
            )
          ) {
            return (
              `${label} ${parameter.name} must be numeric.`
            )
          }
        }

        if (
          parameter.minimum != null &&
          Number(value) <
          Number(
            parameter.minimum
          )
        ) {
          return (
            `${label} ${parameter.name} must be at least ${parameter.minimum}.`
          )
        }

        if (
          parameter.maximum != null &&
          Number(value) >
          Number(
            parameter.maximum
          )
        ) {
          return (
            `${label} ${parameter.name} must be at most ${parameter.maximum}.`
          )
        }

        if (
          parameter.options &&
          !parameter.options.includes(
            value
          )
        ) {
          return (
            `${label} ${parameter.name} must be a supported option.`
          )
        }
      }

      return validateMultiplier(
        expression,
        label
      )
    }

    /*
     * Validate every canonical condition:
     *
     * LEFT EXPRESSION
     *       ↓
     *   OPERATOR
     *       ↓
     * RIGHT EXPRESSION
     */
    for (
      const condition of
      conditions
    ) {
      if (
        !condition.left
      ) {
        return (
          'Every condition must have a left expression.'
        )
      }

      if (
        !condition.operator
      ) {
        return (
          'Every condition must have an operator.'
        )
      }

      if (
        !condition.right
      ) {
        return (
          'Every condition must have a right expression.'
        )
      }

      const leftError =
        validateExpression(
          condition.left,
          'Left expression',
          false
        )

      if (leftError) {
        return leftError
      }

      const rightError =
        validateExpression(
          condition.right,
          'Right expression',
          true
        )

      if (rightError) {
        return rightError
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

    const validationError =
      validateResearch()

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
            'Content-Type':
              'application/json',
          },
          body: JSON.stringify(
            buildResearchRequest()
          ),
        }
      )

      const data =
        await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail ||
          'Failed to start research.'
        )
      }

      const newJobId =
        data.job_id

      if (!newJobId) {
        throw new Error(
          'Research job ID was not returned by the backend.'
        )
      }

      setJobId(newJobId)
      setJobStatus(data.status)
      setJobProgress(
        data.progress ?? 0
      )
      setJobStage(
        data.stage || 'Queued'
      )

      const eventSource =
        new EventSource(
          `${API_BASE_URL}/research/jobs/${newJobId}/stream`
        )

      eventSourceRef.current =
        eventSource

      eventSource.addEventListener(
        'progress',
        async (event) => {
          try {
            const job =
              JSON.parse(
                event.data
              )

            setJobStatus(
              job.status
            )

            setJobProgress(
              job.progress ?? 0
            )

            setJobStage(
              job.stage || ''
            )

            if (
              job.status ===
              'COMPLETED'
            ) {
              eventSource.close()

              if (
                eventSourceRef.current ===
                eventSource
              ) {
                eventSourceRef.current =
                  null
              }

              try {
                const resultResponse =
                  await fetch(
                    `${API_BASE_URL}/research/jobs/${newJobId}`
                  )

                const resultData =
                  await resultResponse.json()

                if (
                  !resultResponse.ok
                ) {
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

            if (
              job.status ===
              'FAILED'
            ) {
              eventSource.close()

              if (
                eventSourceRef.current ===
                eventSource
              ) {
                eventSourceRef.current =
                  null
              }

              setRunError(
                job.error ||
                'Research execution failed.'
              )

              setIsRunning(false)
            }
          } catch {
            eventSource.close()

            if (
              eventSourceRef.current ===
              eventSource
            ) {
              eventSourceRef.current =
                null
            }

            setRunError(
              'Received an invalid progress update from the research server.'
            )

            setIsRunning(false)
          }
        }
      )

      eventSource.onerror =
        () => {
          eventSource.close()

          if (
            eventSourceRef.current ===
            eventSource
          ) {
            eventSourceRef.current =
              null
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

  const saveExperiment = async (
    result
  ) => {
    const response =
      await fetch(
        `${API_BASE_URL}/research/experiments`,
        {
          method: 'POST',
          headers: {
            'Content-Type':
              'application/json',
          },
          body: JSON.stringify({
            research_result:
              result,

            name:
              'Research Experiment',

            notes:
              'Saved from Research Cockpit.',

            tags: [
              ...new Set(
                conditions
                  .map((condition) =>
                    String(
                      condition.feature ||
                      ''
                    ).toUpperCase()
                  )
                  .filter(Boolean)
              ),
            ],
          }),
        }
      )

    const data =
      await response.json()

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
          <span className="section-kicker">
            RESEARCH CONFIGURATION
          </span>

          <h2>
            Configure Historical Research
          </h2>

          <p>
            Select a universe, time periods,
            indicators, conditions and
            evaluation horizons for historical research.
          </p>

          {loadingFeatures && (
            <p className="backend-status">
              Loading research indicators...
            </p>
          )}

          {featureError && (
            <p className="backend-error">
              {featureError}
            </p>
          )}

          {!loadingFeatures &&
            !featureError && (
              <p className="backend-status">
                {features.length} research
                indicators available
              </p>
            )}
        </div>

        <div className="research-status">
          <span className="status-dot"></span>
          {isRunning
            ? 'RUNNING'
            : 'READY'}
        </div>
      </div>

      <div className="config-grid">
        <UniverseConfig
          value={universe}
          onChange={setUniverse}
          isRunning={isRunning}
        />

        <DateRangeConfig
          researchStage={
            researchStage
          }
          developmentStart={
            developmentStart
          }
          developmentEnd={
            developmentEnd
          }
          validationStart={
            validationStart
          }
          validationEnd={
            validationEnd
          }
          holdoutStart={
            holdoutStart
          }
          holdoutEnd={
            holdoutEnd
          }
          onDevelopmentStartChange={
            setDevelopmentStart
          }
          onDevelopmentEndChange={
            setDevelopmentEnd
          }
          onValidationStartChange={
            setValidationStart
          }
          onValidationEndChange={
            setValidationEnd
          }
          onHoldoutStartChange={
            setHoldoutStart
          }
          onHoldoutEndChange={
            setHoldoutEnd
          }
          isRunning={isRunning}
        />
      </div>

      <ConditionBuilder
        conditions={conditions}
        features={features}
        loadingFeatures={
          loadingFeatures
        }
        featureError={
          featureError
        }
        isRunning={isRunning}
        onAddCondition={
          addCondition
        }
        onRemoveCondition={
          removeCondition
        }
        onUpdateCondition={
          updateCondition
        }
        onUpdateFeature={
          updateFeature
        }
      />

      <EvaluationHorizons
        horizons={[
          1, 3, 5, 10
        ]}
        selectedHorizons={
          evaluationHorizons
        }
        onToggle={
          toggleHorizon
        }
        disabled={isRunning}
      />

      <ResearchExecution
        researchStage={researchStage}
        isRunning={isRunning}
        runError={runError}
        onRunResearch={runResearch}
        onCancel={() => {
          setResearchResult(null)
          setJobStatus(null)
          setJobProgress(0)
          setJobStage('')
        }}
        onModify={() => {
          setResearchResult(null)
          setJobStatus(null)
          setJobProgress(0)
          setJobStage('')
        }}
        onProceed={() => {
          if (researchStage === 'development') {
            setResearchStage('validation')
            setResearchResult(null)
            setJobStatus(null)
            setJobProgress(0)
            setJobStage('')
            return
          }

          if (researchStage === 'validation') {
            setResearchStage('testing')
            setResearchResult(null)
            setJobStatus(null)
            setJobProgress(0)
            setJobStage('')
            return
          }

          if (researchStage === 'testing') {
            // Final result remains available for saving.
            return
          }
        }}
        jobProgress={jobProgress}
        jobStage={jobStage}
        jobStatus={jobStatus}
      />

      <ResearchResults
        researchResult={
          researchResult
        }
        onSaveExperiment={
          saveExperiment
        }
      />
    </section>
  )
}

export default ResearchConfig