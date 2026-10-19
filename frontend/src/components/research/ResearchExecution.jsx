import { useEffect, useRef, useState } from 'react'

function ResearchExecution({
  researchStage,
  isRunning,
  runError,
  onRunResearch,
  onCancel,
  onModify,
  onProceed,
  jobProgress,
  jobStage,
  jobStatus,
}) {
  const [displayStage, setDisplayStage] =
    useState(jobStage || 'Starting research')

  const [stageKey, setStageKey] = useState(0)

  const previousStageRef =
    useRef(jobStage)

  useEffect(() => {
    if (!jobStage) return

    if (
      previousStageRef.current &&
      previousStageRef.current !== jobStage
    ) {
      setStageKey((value) => value + 1)
    }

    setDisplayStage(jobStage)
    previousStageRef.current = jobStage
  }, [jobStage])

  const progress = Math.max(
    0,
    Math.min(100, jobProgress || 0),
  )

  const stageLabel =
    researchStage === 'development'
      ? 'DEVELOPMENT'
      : researchStage === 'validation'
        ? 'VALIDATION'
        : 'FINAL TESTING'

  return (
    <>
      {isRunning && (
        <div className="execution-status">
          <div className="execution-status-header">
            <div className="execution-status-title">
              <span className="execution-live-dot" />
              <span>
                {stageLabel} RUNNING
              </span>
            </div>

            <strong>
              {progress}%
            </strong>
          </div>

          <div
            className="execution-progress-track"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <div
              className="execution-progress-bar"
              style={{
                width: `${progress}%`,
              }}
            />
          </div>

          <div
            key={stageKey}
            className="execution-stage-current"
          >
            <span className="execution-stage-spinner" />

            <div className="execution-stage-content">
              <span className="execution-stage-label">
                CURRENT STAGE
              </span>

              <span className="execution-stage-name">
                {displayStage}
              </span>
            </div>
          </div>
        </div>
      )}

      {runError && (
        <div className="run-error">
          <strong>
            Research could not be executed
          </strong>

          <span>
            {runError}
          </span>
        </div>
      )}

      {!isRunning && (
        <div className="run-section">
          <div>
            <strong>
              {researchStage === 'development' &&
                'Ready to run development research?'}

              {researchStage === 'validation' &&
                'Ready to run validation?'}

              {researchStage === 'testing' &&
                'Ready to run final testing?'}
            </strong>

            <span>
              {researchStage === 'development' &&
                'Only the development period will be processed.'}

              {researchStage === 'validation' &&
                'Only the validation period will be processed.'}

              {researchStage === 'testing' &&
                'Only the final holdout period will be processed.'}
            </span>
          </div>

          <button
            className="run-button"
            onClick={onRunResearch}
          >
            {researchStage === 'development' &&
              'RUN DEVELOPMENT'}

            {researchStage === 'validation' &&
              'RUN VALIDATION'}

            {researchStage === 'testing' &&
              'RUN FINAL TESTING'}
          </button>
        </div>
      )}

      {!isRunning &&
        jobStatus === 'COMPLETED' &&
        !runError && (
          <div className="research-stage-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={onCancel}
            >
              CANCEL
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={onModify}
            >
              MODIFY
            </button>

            {researchStage === 'development' && (
              <button
                type="button"
                className="primary-button"
                onClick={onProceed}
              >
                PROCEED TO VALIDATION
              </button>
            )}

            {researchStage === 'validation' && (
              <button
                type="button"
                className="primary-button"
                onClick={onProceed}
              >
                PROCEED TO TESTING
              </button>
            )}

            {researchStage === 'testing' && (
              <button
                type="button"
                className="primary-button"
                onClick={onProceed}
              >
                SAVE EXPERIMENT
              </button>
            )}
          </div>
        )}
    </>
  )
}

export default ResearchExecution