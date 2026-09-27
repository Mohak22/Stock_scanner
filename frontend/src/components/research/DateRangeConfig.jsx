function DateRangeConfig({
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
    optional = false,
  ) => (
    <div className="research-split">
      <div className="research-split-header">
        <span className="research-split-label">
          {label}{optional ? ' · OPTIONAL' : ''}
        </span>
      </div>

      <div className="date-inputs">
        <input
          type="date"
          value={startDate || ''}
          onChange={(event) => onStartChange(event.target.value)}
          onClick={openDatePicker}
          disabled={isRunning}
        />

        <span>→</span>

        <input
          type="date"
          value={endDate || ''}
          onChange={(event) => onEndChange(event.target.value)}
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
          <label>Research Evaluation Periods</label>

          <span className="field-help">
            Development is iterative. Validation evaluates an unseen
            period. Final Holdout is inspected only when the candidate
            is ready to lock.
          </span>
        </div>
      </div>

      <div className="research-splits">
        {renderDateRange(
          'DEVELOPMENT',
          developmentStart,
          developmentEnd,
          onDevelopmentStartChange,
          onDevelopmentEndChange,
          'Primary research period used to develop the hypothesis.',
        )}

        {renderDateRange(
          'VALIDATION',
          validationStart,
          validationEnd,
          onValidationStartChange,
          onValidationEndChange,
          'Unseen period used to evaluate a candidate without touching the holdout.',
          true,
        )}

        {renderDateRange(
          'FINAL HOLDOUT',
          holdoutStart,
          holdoutEnd,
          onHoldoutStartChange,
          onHoldoutEndChange,
          'Final historical evidence. Changing the candidate after inspection creates a new experiment.',
          true,
        )}
      </div>
    </div>
  )
}

export default DateRangeConfig
