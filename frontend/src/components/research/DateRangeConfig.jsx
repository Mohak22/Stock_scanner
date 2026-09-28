function DateRangeConfig({
  researchStage,
  developmentStart,
  developmentEnd,
  validationStart,
  validationEnd,
  holdoutStart,
  holdoutEnd,
  onDevelopmentStartChange,
  onDevelopmentEndChange,
  onValidationStartChange,
  onValidationEndChange,
  onHoldoutStartChange,
  onHoldoutEndChange,
  isRunning,
}) {
  const openDatePicker = (event) => {
    if (isRunning) return

    const input = event.currentTarget

    if (input.showPicker) {
      input.showPicker()
    }
  }

  const renderDateRange = (
    label,
    startDate,
    endDate,
    onStartChange,
    onEndChange,
    helpText,
  ) => (
    <div className="research-split">
      <div className="research-split-header">
        <span className="research-split-label">
          {label}
        </span>
      </div>

      <div className="date-inputs">
        <input
          type="date"
          value={startDate || ''}
          onChange={(event) =>
            onStartChange(event.target.value)
          }
          onClick={openDatePicker}
          disabled={isRunning}
        />

        <span>→</span>

        <input
          type="date"
          value={endDate || ''}
          onChange={(event) =>
            onEndChange(event.target.value)
          }
          onClick={openDatePicker}
          disabled={isRunning}
        />
      </div>

      <span className="field-help">
        {helpText}
      </span>
    </div>
  )

  return (
    <div className="config-card research-period-card">
      <div className="config-card-header">
        <div>
          <label>Research Evaluation Period</label>

          <span className="field-help">
            {researchStage === 'development' &&
              'Use this period to iteratively develop and refine the candidate.'}

            {researchStage === 'validation' &&
              'Validation evaluates the candidate on an unseen period.'}

            {researchStage === 'testing' &&
              'Final testing evaluates the candidate on the untouched holdout period.'}
          </span>
        </div>
      </div>

      <div className="research-splits">
        {researchStage === 'development' &&
          renderDateRange(
            'DEVELOPMENT',
            developmentStart,
            developmentEnd,
            onDevelopmentStartChange,
            onDevelopmentEndChange,
            'Primary research period used for iterative development.',
          )}

        {researchStage === 'validation' &&
          renderDateRange(
            'VALIDATION',
            validationStart,
            validationEnd,
            onValidationStartChange,
            onValidationEndChange,
            'Unseen historical period used to evaluate the candidate.',
          )}

        {researchStage === 'testing' &&
          renderDateRange(
            'FINAL TESTING',
            holdoutStart,
            holdoutEnd,
            onHoldoutStartChange,
            onHoldoutEndChange,
            'Final holdout period. Do not modify the candidate after inspecting this result.',
          )}
      </div>
    </div>
  )
}

export default DateRangeConfig