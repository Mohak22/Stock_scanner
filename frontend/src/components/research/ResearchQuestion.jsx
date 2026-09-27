function ResearchQuestion({
  question,
  hypothesis,
  onQuestionChange,
  onHypothesisChange,
}) {
  return (
    <div className="research-question">
      <label>Research Question</label>

      <input
        type="text"
        value={question}
        onChange={(event) => onQuestionChange(event.target.value)}
        placeholder="Example: Can a one-day price spike persist over the next few sessions?"
      />

      <label>Hypothesis</label>

      <textarea
        value={hypothesis}
        onChange={(event) => onHypothesisChange(event.target.value)}
        placeholder="State the falsifiable market hypothesis you want to investigate..."
        rows={3}
      />
    </div>
  )
}

export default ResearchQuestion
