function DateRangeConfig({
  trainingStart,
  trainingEnd,
  validationStart,
  validationEnd,
  testingStart,
  testingEnd,
  onTrainingStartChange,
  onTrainingEndChange,
  onValidationStartChange,
  onValidationEndChange,
  onTestingStartChange,
  onTestingEndChange,
  isRunning,
}) {
  const openDatePicker = (event) => {
    if (isRunning) {
      return
    }

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
  ) => {
    return (
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
  }

  return (
    <div className="config-card research-period-card">

      <div className="config-card-header">

        <div>
          <label>
            Research Evaluation Periods
          </label>

          <span className="field-help">
            Define the historical periods used for
            training, validation and final testing.
          </span>
        </div>

      </div>

      <div className="research-splits">

        {renderDateRange(
          'TRAINING',
          trainingStart,
          trainingEnd,
          onTrainingStartChange,
          onTrainingEndChange,
          'Used to develop and evaluate the initial hypothesis.',
        )}

        {renderDateRange(
          'VALIDATION',
          validationStart,
          validationEnd,
          onValidationStartChange,
          onValidationEndChange,
          'Used to evaluate the hypothesis on unseen data.',
        )}

        {renderDateRange(
          'TESTING',
          testingStart,
          testingEnd,
          onTestingStartChange,
          onTestingEndChange,
          'Final unseen period used before the experiment is locked.',
        )}

      </div>

    </div>
  )
}

export default DateRangeConfig