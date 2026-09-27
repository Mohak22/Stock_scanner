import { useEffect, useState } from 'react'

const API_BASE = 'http://127.0.0.1:8000'

function formatDate(value) {
    if (!value) {
        return '—'
    }

    const date = new Date(value)

    if (Number.isNaN(date.getTime())) {
        return value
    }

    return date.toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    })
}

function StrategyDetail({
    strategy,
    onBack,
}) {
    const [strategyData, setStrategyData] =
        useState(strategy)

    const [isLoading, setIsLoading] =
        useState(true)

    const [error, setError] =
        useState('')

    const [isLocking, setIsLocking] =
        useState(false)

    const [lockError, setLockError] =
        useState('')

    useEffect(() => {
        let cancelled = false

        async function loadStrategy() {
            try {
                setIsLoading(true)
                setError('')

                const response = await fetch(
                    `${API_BASE}/research/strategies/${encodeURIComponent(
                        strategy.strategy_slug
                    )}/v${strategy.version}`
                )

                const data =
                    await response.json().catch(() => null)

                if (!response.ok) {
                    throw new Error(
                        data?.detail ||
                        `Failed to load strategy (${response.status})`
                    )
                }

                if (!cancelled) {
                    setStrategyData(data)
                }
            } catch (err) {
                if (!cancelled) {
                    setError(
                        err.message ||
                        'Failed to load strategy.'
                    )
                }
            } finally {
                if (!cancelled) {
                    setIsLoading(false)
                }
            }
        }

        loadStrategy()

        return () => {
            cancelled = true
        }
    }, [
        strategy.strategy_slug,
        strategy.version,
    ])

    async function lockStrategy() {
        try {
            setIsLocking(true)
            setLockError('')

            const response = await fetch(
                `${API_BASE}/research/strategies/${encodeURIComponent(
                    strategyData.strategy_slug
                )}/v${strategyData.version}/lock`,
                {
                    method: 'POST',
                }
            )

            const data =
                await response.json().catch(() => null)

            if (!response.ok) {
                throw new Error(
                    data?.detail ||
                    `Failed to lock strategy (${response.status})`
                )
            }

            setStrategyData(data)
        } catch (err) {
            setLockError(
                err.message ||
                'Failed to lock strategy.'
            )
        } finally {
            setIsLocking(false)
        }
    }

    if (isLoading) {
        return (
            <section className="strategy-detail">
                <div className="experiment-state">
                    Loading strategy...
                </div>
            </section>
        )
    }

    if (error) {
        return (
            <section className="strategy-detail">

                <button
                    className="experiment-back-button"
                    onClick={onBack}
                >
                    ← BACK TO STRATEGY LIBRARY
                </button>

                <div className="experiment-state experiment-error">

                    <strong>
                        Unable to load strategy
                    </strong>

                    <span>
                        {error}
                    </span>

                </div>

            </section>
        )
    }

    if (!strategyData) {
        return null
    }

    const isLocked =
        strategyData.status === 'LOCKED'

    return (
        <section className="strategy-detail">

            <div className="strategy-detail-top">

                <button
                    className="experiment-back-button"
                    onClick={onBack}
                >
                    ← BACK TO STRATEGY LIBRARY
                </button>

            </div>

            <div className="strategy-detail-header">

                <div>

                    <div className="section-eyebrow">
                        STRATEGY
                    </div>

                    <h1>
                        {strategyData.strategy_name}
                    </h1>

                    <div className="strategy-detail-id">
                        {strategyData.strategy_slug}
                    </div>

                </div>

                <span className="strategy-status-badge">
                    {strategyData.status}
                </span>

            </div>

            <div className="strategy-detail-meta">

                <div>
                    <span>VERSION</span>
                    <strong>
                        v{strategyData.version}
                    </strong>
                </div>

                <div>
                    <span>CREATED</span>
                    <strong>
                        {formatDate(
                            strategyData.created_at
                        )}
                    </strong>
                </div>

                <div>
                    <span>SOURCE EXPERIMENT</span>
                    <strong>
                        {strategyData.source_experiment_id}
                    </strong>
                </div>

                <div>
                    <span>LOCKED</span>
                    <strong>
                        {formatDate(
                            strategyData.locked_at
                        )}
                    </strong>
                </div>

            </div>

            {strategyData.description && (
                <div className="strategy-detail-description">

                    <span className="detail-section-label">
                        DESCRIPTION
                    </span>

                    <p>
                        {strategyData.description}
                    </p>

                </div>
            )}

            {strategyData.version_notes && (
                <div className="strategy-detail-description">

                    <span className="detail-section-label">
                        VERSION NOTES
                    </span>

                    <p>
                        {strategyData.version_notes}
                    </p>

                </div>
            )}

            <div className="strategy-detail-section">
                <div className="detail-section-heading">
                    <div>
                        <span className="section-eyebrow">FROZEN RESEARCH EVIDENCE</span>
                        <h2>{strategyData.research_question || '—'}</h2>
                        <p>{strategyData.hypothesis || '—'}</p>
                    </div>
                </div>
            </div>

            <div className="strategy-detail-section">

                <div className="detail-section-heading">

                    <div>

                        <span className="section-eyebrow">
                            RESEARCH SNAPSHOT
                        </span>

                        <h2>
                            Strategy Definition
                        </h2>

                    </div>

                </div>

                <div className="strategy-definition-card">

                    <div>
                        <span>
                            UNIVERSE
                        </span>

                        <strong>
                            {strategyData.research_config?.universe
                                ? JSON.stringify(
                                    strategyData.research_config.universe
                                )
                                : '—'}
                        </strong>
                    </div>

                    <div>
                        <span>
                            FEATURES
                        </span>

                        <strong>
                            {strategyData.research_config?.features?.length ??
                                0}
                        </strong>
                    </div>

                    <div>
                        <span>
                            ENTRY CONDITIONS
                        </span>

                        <strong>
                            {strategyData.research_config?.entry_conditions?.length ??
                                0}
                        </strong>
                    </div>

                    <div>
                        <span>
                            EVALUATION HORIZONS
                        </span>

                        <strong>
                            {strategyData.research_config?.evaluation_horizons?.join(
                                ', '
                            ) || '—'}
                        </strong>
                    </div>

                </div>

            </div>

            <div className="strategy-detail-section">

                <div className="detail-section-heading">
                    <div>
                        <span className="section-eyebrow">
                            LIFECYCLE
                        </span>
                        <h2>Strategy State</h2>
                    </div>
                </div>

                <div className="strategy-lifecycle">
                    <div className="strategy-lifecycle-step active">
                        <span>01</span>
                        <strong>DRAFT</strong>
                        <small>Strategy created from locked evidence</small>
                    </div>

                    <div className="strategy-lifecycle-line" />

                    <div className="strategy-lifecycle-step">
                        <span>02</span>
                        <strong>LOCKED</strong>
                        <small>Frozen strategy definition</small>
                    </div>

                    <div className="strategy-lifecycle-line" />

                    <div className="strategy-lifecycle-step">
                        <span>03</span>
                        <strong>FORWARD TESTING</strong>
                        <small>Evaluate only on future market data</small>
                    </div>

                    <div className="strategy-lifecycle-line" />

                    <div className="strategy-lifecycle-step">
                        <span>04</span>
                        <strong>DEPLOYMENT</strong>
                        <small>Execution integration after forward testing</small>
                    </div>
                </div>
            </div>

            {!isLocked && (
                <div className="strategy-detail-actions">

                    {lockError && (
                        <div className="strategy-form-error">
                            {lockError}
                        </div>
                    )}

                    <button
                        className="strategy-create-button"
                        onClick={lockStrategy}
                        disabled={isLocking}
                    >
                        {isLocking
                            ? 'LOCKING...'
                            : 'LOCK STRATEGY'}
                    </button>

                </div>
            )}

            {isLocked && (
                <div className="strategy-locked-message">
                    Strategy version is locked and ready for
                    future forward-testing integration.
                </div>
            )}

        </section>
    )
}

export default StrategyDetail