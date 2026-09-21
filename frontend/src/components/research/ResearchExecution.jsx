import { useEffect, useRef, useState } from 'react'

function ResearchExecution({
  isRunning,
  runError,
  onRunResearch,
  jobProgress,
  jobStage,
  jobStatus,
}) {
  const [displayStage, setDisplayStage] = useState(jobStage || 'Starting research')
  const [stageKey, setStageKey] = useState(0)
  const previousStageRef = useRef(jobStage)

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

  const progress = Math.max(0, Math.min(100, jobProgress || 0))

  return (
    <>
      {isRunning && (
        <div className="execution-status">

          {/* HEADER */}
          <div className="execution-status-header">
            <div className="execution-status-title">
              <span className="execution-live-dot" />
              <span>RESEARCH ENGINE EXECUTING</span>
            </div>

            <strong>{progress}%</strong>
          </div>

          {/* WINDOWS-STYLE PROGRESS BAR */}
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
            >
              <div className="execution-progress-glow" />
            </div>
          </div>

          {/* CURRENT STAGE */}
          <div className="execution-stage-window">

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

          {/* STATUS META */}
          <div className="execution-status-meta">
            <span>
              {progress < 100
                ? 'Research engine is processing your configuration'
                : 'Finalizing research results'}
            </span>

            <span className="execution-status-badge">
              {jobStatus || 'RUNNING'}
            </span>
          </div>
        </div>
      )}

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
              ? displayStage ||
                'The backend research engine is processing your configuration.'
              : 'Running research does not save an experiment automatically.'}
          </span>
        </div>

        <button
          className="run-button"
          onClick={onRunResearch}
          disabled={isRunning}
        >
          {isRunning
            ? `${progress}% RUNNING...`
            : 'RUN RESEARCH'}
        </button>
      </div>
    </>
  )
}

export default ResearchExecution