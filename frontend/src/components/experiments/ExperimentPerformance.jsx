import { useState } from 'react'

function formatNumber(value, suffix = '') {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
    return `${Number(value).toFixed(2)}${suffix}`
}

function StagePerformance({ stage }) {
    const summary = stage?.summary || {}
    const performance = stage?.performance || {}
    const horizons = Object.keys(performance)

    return (
        <div className="experiment-performance">
            <div className="experiment-summary-grid">
                <div className="experiment-summary-card"><span>Signals</span><strong>{summary.signal_count ?? '—'}</strong></div>
                <div className="experiment-summary-card"><span>Signal Rate</span><strong>{formatNumber(summary.signal_rate, '%')}</strong></div>
                <div className="experiment-summary-card"><span>Stocks With Signals</span><strong>{summary.stocks_with_signals ?? '—'}</strong></div>
                <div className="experiment-summary-card"><span>Horizons</span><strong>{horizons.length}</strong></div>
            </div>
            {horizons.length > 0 && (
                <div className="experiment-performance-table-wrapper">
                    <table className="experiment-performance-table">
                        <thead><tr><th>HORIZON</th><th>AVG RETURN</th><th>MEDIAN</th><th>POSITIVE</th><th>OBSERVATIONS</th></tr></thead>
                        <tbody>
                            {horizons.map((horizon) => {
                                const data = performance[horizon]
                                return <tr key={horizon}><td><strong>{horizon}</strong></td><td>{formatNumber(data.average_return, '%')}</td><td>{formatNumber(data.median_return, '%')}</td><td>{formatNumber(data.positive_return_pct, '%')}</td><td>{data.observations ?? '—'}</td></tr>
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}

function ExperimentPerformance({ result }) {
    const [activeStage, setActiveStage] = useState('development')
    const stages = [['development', 'DEVELOPMENT'], ['validation', 'VALIDATION'], ['final_holdout', 'FINAL HOLDOUT']]

    return (
        <div>
            <div className="analysis-tabs research-stage-tabs">
                {stages.map(([key, label]) => (
                    <button key={key} className={'analysis-tab ' + (activeStage === key ? 'active' : '')} disabled={!result?.[key]} onClick={() => setActiveStage(key)}>
                        <span className="tab-number">{key === 'development' ? '01' : key === 'validation' ? '02' : '03'}</span>
                        <span><strong>{label}</strong><small>{result?.[key] ? 'Evaluation available' : 'Not evaluated'}</small></span>
                    </button>
                ))}
            </div>
            {result?.[activeStage] ? <StagePerformance stage={result[activeStage]} /> : <div className="experiment-detail-empty">This stage has not been evaluated.</div>}
        </div>
    )
}

export default ExperimentPerformance