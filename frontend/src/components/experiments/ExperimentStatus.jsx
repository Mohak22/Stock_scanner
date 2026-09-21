function ExperimentStatus({ status }) {
  const normalizedStatus = status || 'UNKNOWN'

  return (
    <span
      className={`experiment-status experiment-status-${normalizedStatus.toLowerCase()}`}
    >
      {normalizedStatus}
    </span>
  )
}

export default ExperimentStatus