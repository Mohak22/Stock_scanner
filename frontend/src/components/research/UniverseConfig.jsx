function UniverseConfig({ value, onChange }) {
  return (
    <div className="config-card">
      <label>Universe</label>

      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="all_stocks">All Stocks</option>
        <option value="symbols" disabled>
          Custom Symbols — backend support later
        </option>
      </select>

      <span className="field-help">
        Select the stocks that should participate in the research.
      </span>
    </div>
  )
}

export default UniverseConfig
