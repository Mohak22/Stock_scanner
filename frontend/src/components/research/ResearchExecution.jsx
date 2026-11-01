import { useState } from 'react'

function ResearchExecution({
  researchStage,
  isRunning,
  runError,
  onRunResearch,
  onCancel,
  onModify,
  onProceed,
  onSaveExperiment,
  researchResult,
  jobProgress,
  jobStage,
  jobStatus,
}) {
  const [isSaving, setIsSaving] = useState(false)

  const displayStage =
    jobStage || 'Starting research'

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

  const handleSaveExperiment = async () => {
    if (isSaving) return

    if (!researchResult) {
      window.alert(
        'No completed research result is available to save.',
      )
      return
    }

    if (typeof onSaveExperiment !== 'function') {
      window.alert(
        'Save failed: the save function is not connected.',
      )
      return
    }

    setIsSaving(true)

    try {
      const result = await onSaveExperiment(researchResult)

      if (!result?.experiment_id) {
        throw new Error(
          'The server did not return an experiment ID. Verify whether the experiment was saved.',
        )
      }

      window.alert(
        `Experiment saved successfully.\n\nExperiment ID: ${result.experiment_id}`,
      )
    } catch (error) {
      console.error('Save experiment failed:', error)

      window.alert(
        `Experiment could not be saved.\n\n${error.message || 'Unknown error'}`,
      )
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <>
      {isRunning && (
        <div className="execution-status">
          <div className="execution-status-header">
            <div className="execution-status-title">
              <span className="execution-live-dot" />
              <span>{stageLabel} RUNNING</span>
            </div>

            <strong>{progress}%</strong>
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
              style={{ width: `${progress}%` }}
            />
          </div>

          <div
            key={displayStage}
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
          <strong>Research could not be executed</strong>
          <span>{runError}</span>
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
            type="button"
            className="run-button"
            onClick={onRunResearch}
            disabled={isSaving}
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
              disabled={isSaving}
            >
              CANCEL
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={onModify}
              disabled={isSaving}
            >
              MODIFY
            </button>

            {researchStage === 'development' && (
              <button
                type="button"
                className="primary-button"
                onClick={onProceed}
                disabled={isSaving}
              >
                PROCEED TO VALIDATION
              </button>
            )}

            {researchStage === 'validation' && (
              <button
                type="button"
                className="primary-button"
                onClick={onProceed}
                disabled={isSaving}
              >
                PROCEED TO TESTING
              </button>
            )}

            {researchStage === 'testing' && (
              <button
                type="button"
                className="primary-button"
                onClick={handleSaveExperiment}
                disabled={isSaving}
              >
                {isSaving
                  ? 'SAVING EXPERIMENT...'
                  : 'SAVE EXPERIMENT'}
              </button>
            )}
          </div>
        )}
    </>
  )
}

export default ResearchExecution