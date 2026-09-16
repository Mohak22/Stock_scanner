function ResearchQuestion({ value, onChange }) {
  return (
    <div className="research-question">
      <label>Research Question</label>

      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Example: Find stocks that are oversold but showing signs of accumulation..."
      />
    </div>
  )
}

export default ResearchQuestion
