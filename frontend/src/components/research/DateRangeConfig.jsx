function DateRangeConfig({
  startDate,
  endDate,
  onStartChange,
  onEndChange,
  isRunning,
}) {
  const openDatePicker = (event) => {
    if (isRunning) return

    const input = event.currentTarget

    if (input.showPicker) {
      input.showPicker()
    }
  }

  return (
    <div className="config-card">
      <label>Research Period</label>

      <div className="date-inputs">
        <input
          type="date"
          value={startDate}
          onChange={(event) => onStartChange(event.target.value)}
          onClick={openDatePicker}
          disabled={isRunning}
        />

        <span>→</span>

        <input
          type="date"
          value={endDate}
          onChange={(event) => onEndChange(event.target.value)}
          onClick={openDatePicker}
          disabled={isRunning}
        />
      </div>

      <span className="field-help">
        Historical period used for signal generation and evaluation.
      </span>
    </div>
  )
}

export default DateRangeConfig