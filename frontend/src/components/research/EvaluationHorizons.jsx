function EvaluationHorizons({ horizons, selectedHorizons, onToggle, disabled }) {
  return (
    <div className="horizons-section">
      <div>
        <label>Evaluation Horizons</label>
        <span>
          Forward-return periods calculated by the research engine.
        </span>
      </div>

      <div className="horizon-options">
        {horizons.map((horizon) => (
          <button
            key={horizon}
            className={
              selectedHorizons.includes(horizon)
                ? 'horizon-button selected'
                : 'horizon-button'
            }
            onClick={() => onToggle(horizon)}
            disabled={disabled}
          >
            T+{horizon}
          </button>
        ))}
      </div>
    </div>
  )
}

export default EvaluationHorizons
