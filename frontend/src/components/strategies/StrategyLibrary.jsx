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

function StrategyLibrary({
    onOpenStrategy,
}) {
    const [strategies, setStrategies] = useState([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState('')

    useEffect(() => {
        let cancelled = false

        async function loadStrategies() {
            try {
                setIsLoading(true)
                setError('')

                const response = await fetch(
                    `${API_BASE}/research/strategies`
                )

                const data =
                    await response.json().catch(() => null)

                if (!response.ok) {
                    throw new Error(
                        data?.detail ||
                        `Failed to load strategies (${response.status})`
                    )
                }

                if (!cancelled) {
                    setStrategies(
                        data?.strategies || []
                    )
                }
            } catch (err) {
                if (!cancelled) {
                    setError(
                        err.message ||
                        'Failed to load strategies.'
                    )
                }
            } finally {
                if (!cancelled) {
                    setIsLoading(false)
                }
            }
        }

        loadStrategies()

        return () => {
            cancelled = true
        }
    }, [])

    if (isLoading) {
        return (
            <section className="strategy-library">
                <div className="experiment-state">
                    Loading strategies...
                </div>
            </section>
        )
    }

    if (error) {
        return (
            <section className="strategy-library">
                <div className="experiment-state experiment-error">
                    <strong>
                        Unable to load strategies
                    </strong>

                    <span>{error}</span>
                </div>
            </section>
        )
    }

    return (
        <section className="strategy-library">

            <div className="strategy-library-header">

                <div>
                    <div className="section-eyebrow">
                        STRATEGY SYSTEM
                    </div>

                    <h1>
                        Strategy Library
                    </h1>

                    <p>
                        Versioned strategies promoted from
                        locked research experiments.
                    </p>
                </div>

                <div className="strategy-library-count">
                    <span>STRATEGIES</span>
                    <strong>
                        {strategies.length}
                    </strong>
                </div>

            </div>

            {strategies.length === 0 ? (
                <div className="strategy-empty-state">
                    <div className="section-eyebrow">
                        NO STRATEGIES
                    </div>

                    <h2>
                        Strategy library is empty
                    </h2>

                    <p>
                        Lock a research experiment and
                        promote it to a strategy.
                    </p>
                </div>
            ) : (
                <div className="strategy-library-grid">

                    {strategies.map((strategy) => (
                        <article
                            className="strategy-card"
                            key={`${strategy.strategy_slug}-v${strategy.version}`}
                        >

                            <div className="strategy-card-top">

                                <div>
                                    <div className="strategy-card-label">
                                        STRATEGY
                                    </div>

                                    <h2>
                                        {strategy.strategy_name}
                                    </h2>

                                    <div className="strategy-card-slug">
                                        {strategy.strategy_slug}
                                    </div>
                                </div>

                                <span className="strategy-status-badge">
                                    {strategy.status}
                                </span>

                            </div>

                            <div className="strategy-card-version">
                                <span>VERSION</span>

                                <strong>
                                    v{strategy.version}
                                </strong>
                            </div>

                            <div className="strategy-card-meta">

                                <div>
                                    <span>
                                        SOURCE EXPERIMENT
                                    </span>

                                    <strong>
                                        {strategy.source_experiment_id ||
                                            '—'}
                                    </strong>
                                </div>

                                <div>
                                    <span>
                                        CREATED
                                    </span>

                                    <strong>
                                        {formatDate(
                                            strategy.created_at
                                        )}
                                    </strong>
                                </div>

                            </div>

                            {strategy.description && (
                                <p className="strategy-card-description">
                                    {strategy.description}
                                </p>
                            )}

                            <div className="strategy-card-actions">

                                <button
                                    className="strategy-open-button"
                                    onClick={() =>
                                        onOpenStrategy(
                                            strategy
                                        )
                                    }
                                >
                                    OPEN STRATEGY
                                </button>

                            </div>

                        </article>
                    ))}

                </div>
            )}

        </section>
    )
}

export default StrategyLibrary