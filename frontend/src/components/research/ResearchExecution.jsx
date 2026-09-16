function ResearchExecution({ isRunning, runError, onRunResearch }) {
  return (
    <>
      {isRunning && (
        <div className="execution-status">
          <div className="execution-status-header">
            <span>RESEARCH ENGINE EXECUTING</span>
            <strong>PROCESSING</strong>
          </div>

          <div className="execution-progress-track">
            <div className="execution-progress-bar"></div>
          </div>

          <div className="execution-status-meta">
            <span>Loading historical data</span>
            <span>Calculating features</span>
            <span>Evaluating signals</span>
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
              ? 'The backend research engine is processing your configuration.'
              : 'Running research does not save an experiment automatically.'}
          </span>
        </div>

        <button
          className="run-button"
          onClick={onRunResearch}
          disabled={isRunning}
        >
          {isRunning ? 'RUNNING...' : 'RUN RESEARCH'}
        </button>
      </div>
    </>
  )
}

export default ResearchExecution
