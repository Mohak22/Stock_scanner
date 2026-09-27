function ExperimentConfig({ config }) {
    if (!config) return <div className="experiment-detail-empty">No research configuration available.</div>
    const universe = config.universe || {}
    const features = config.features || []
    const conditions = config.entry_conditions || []
    const horizons = config.evaluation_horizons || []
    const formatDate = (value) => value ? String(value).slice(0, 10) : '—'

    return (
        <div className="experiment-config-grid">
            <div className="experiment-config-card"><span className="config-label">RESEARCH QUESTION</span><strong>{config.research_question || '—'}</strong></div>
            <div className="experiment-config-card"><span className="config-label">HYPOTHESIS</span><strong>{config.hypothesis || '—'}</strong></div>
            <div className="experiment-config-card"><span className="config-label">DEVELOPMENT</span><strong>{formatDate(config.development_start)} → {formatDate(config.development_end)}</strong></div>
            <div className="experiment-config-card"><span className="config-label">VALIDATION</span><strong>{config.validation_start ? formatDate(config.validation_start) + ' → ' + formatDate(config.validation_end) : 'Not evaluated'}</strong></div>
            <div className="experiment-config-card"><span className="config-label">FINAL HOLDOUT</span><strong>{config.holdout_start ? formatDate(config.holdout_start) + ' → ' + formatDate(config.holdout_end) : 'Not evaluated'}</strong></div>
            <div className="experiment-config-card"><span className="config-label">UNIVERSE</span><strong>{universe.type || '—'}</strong>{universe.symbols?.length > 0 && <span className="config-secondary">{universe.symbols.length} symbols</span>}</div>
            <div className="experiment-config-card"><span className="config-label">FEATURES</span><div className="config-list">{features.length > 0 ? features.map((feature, index) => <span key={index}>{feature.type}{feature.period ? ' (' + feature.period + ')' : ''}</span>) : <span>—</span>}</div></div>
            <div className="experiment-config-card"><span className="config-label">ENTRY CONDITIONS</span><div className="config-list">{conditions.length > 0 ? conditions.map((condition, index) => <span key={index}>{condition.feature} {condition.operator} {condition.value}</span>) : <span>—</span>}</div></div>
            <div className="experiment-config-card"><span className="config-label">EVALUATION HORIZONS</span><div className="config-horizon-list">{horizons.length > 0 ? horizons.map((horizon) => <span key={horizon}>T+{horizon}</span>) : <span>—</span>}</div></div>
            <div className="experiment-config-card"><span className="config-label">SIGNAL / OUTCOME</span><strong>{config.signal_timing?.entry || '—'}</strong><span className="config-secondary">{config.outcome_definition?.anchor || '—'} · {config.outcome_definition?.price_basis || '—'}</span></div>
        </div>
    )
}

export default ExperimentConfig