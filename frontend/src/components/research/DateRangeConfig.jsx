function DateRangeConfig({ startDate, endDate, onStartChange, onEndChange }) {
  return (
    <div className="config-card">
      <label>Research Period</label>

      <div className="date-inputs">
        <input
          type="date"
          value={startDate}
          onChange={(event) => onStartChange(event.target.value)}
        />

        <span>→</span>

        <input
          type="date"
          value={endDate}
          onChange={(event) => onEndChange(event.target.value)}
        />
      </div>

      <span className="field-help">
        Historical period used for signal generation and evaluation.
      </span>
    </div>
  )
}

export default DateRangeConfig
