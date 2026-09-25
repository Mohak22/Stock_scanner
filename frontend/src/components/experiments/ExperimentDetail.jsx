import { useEffect, useState } from 'react'
import ExperimentStatus from './ExperimentStatus'
import ExperimentConfig from './ExperimentConfig'
import ExperimentPerformance from './ExperimentPerformance'

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

function ExperimentDetail({
    experimentId,
    onBack,
}) {
    const [experiment, setExperiment] = useState(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState('')

    const [strategyName, setStrategyName] = useState('')
    const [strategyDescription, setStrategyDescription] = useState('')
    const [versionNotes, setVersionNotes] = useState('')

    const [isCreatingStrategy, setIsCreatingStrategy] = useState(false)
    const [strategyError, setStrategyError] = useState('')
    const [createdStrategy, setCreatedStrategy] = useState(null)

    useEffect(() => {
        let cancelled = false

        async function loadExperiment() {
            try {
                setIsLoading(true)
                setError('')

                const response = await fetch(
                    `${API_BASE}/research/experiments/${experimentId}`
                )

                if (!response.ok) {
                    const data =
                        await response.json().catch(() => null)

                    throw new Error(
                        data?.detail ||
                        `Failed to load experiment (${response.status})`
                    )
                }

                const data = await response.json()

                if (!cancelled) {
                    setExperiment(data)
                }
            } catch (err) {
                if (!cancelled) {
                    setError(
                        err.message ||
                        'Failed to load experiment.'
                    )
                }
            } finally {
                if (!cancelled) {
                    setIsLoading(false)
                }
            }
        }

        loadExperiment()

        return () => {
            cancelled = true
        }
    }, [experimentId])

    async function createStrategy() {
        const trimmedName = strategyName.trim()

        if (!trimmedName) {
            setStrategyError(
                'Please enter a strategy name.'
            )
            return
        }

        try {
            setIsCreatingStrategy(true)
            setStrategyError('')

            const response = await fetch(
                `${API_BASE}/research/strategies`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        experiment_id:
                            experiment.experiment_id,
                        strategy_name:
                            trimmedName,
                        description:
                            strategyDescription.trim() || null,
                        version_notes:
                            versionNotes.trim() || null,
                    }),
                }
            )

            const data =
                await response.json().catch(() => null)

            if (!response.ok) {
                throw new Error(
                    data?.detail ||
                    `Failed to create strategy (${response.status})`
                )
            }

            setCreatedStrategy(data)
        } catch (err) {
            setStrategyError(
                err.message ||
                'Failed to create strategy.'
            )
        } finally {
            setIsCreatingStrategy(false)
        }
    }

    if (isLoading) {
        return (
            <section className="experiment-detail">
                <div className="experiment-state">
                    Loading experiment...
                </div>
            </section>
        )
    }

    if (error) {
        return (
            <section className="experiment-detail">
                <button
                    className="experiment-back-button"
                    onClick={onBack}
                >
                    ← BACK TO HISTORY
                </button>

                <div className="experiment-state experiment-error">
                    <strong>
                        Unable to load experiment
                    </strong>

                    <span>{error}</span>
                </div>
            </section>
        )
    }

    if (!experiment) {
        return null
    }

    const researchResult =
        experiment.research_result || {}

    const researchConfig =
        researchResult.research_config || {}

    const isLocked =
        experiment.status === 'LOCKED'

    return (
        <section className="experiment-detail">

            <div className="experiment-detail-top">
                <button
                    className="experiment-back-button"
                    onClick={onBack}
                >
                    ← BACK TO HISTORY
                </button>
            </div>

            <div className="experiment-detail-header">

                <div>
                    <div className="section-eyebrow">
                        SAVED EXPERIMENT
                    </div>

                    <h1>
                        {experiment.name ||
                            'Untitled Experiment'}
                    </h1>

                    <div className="experiment-detail-id">
                        {experiment.experiment_id}
                    </div>
                </div>

                <ExperimentStatus
                    status={experiment.status}
                />

            </div>

            <div className="experiment-detail-meta">

                <div>
                    <span>CREATED</span>
                    <strong>
                        {formatDate(
                            experiment.created_at
                        )}
                    </strong>
                </div>

                <div>
                    <span>LOCKED</span>
                    <strong>
                        {formatDate(
                            experiment.locked_at
                        )}
                    </strong>
                </div>

                <div>
                    <span>TAGS</span>

                    <div className="experiment-tags">
                        {experiment.tags?.length > 0 ? (
                            experiment.tags.map((tag) => (
                                <span
                                    className="experiment-tag"
                                    key={tag}
                                >
                                    {tag}
                                </span>
                            ))
                        ) : (
                            <span className="no-tags">
                                —
                            </span>
                        )}
                    </div>
                </div>

            </div>

            {experiment.notes && (
                <div className="experiment-notes">
                    <span className="detail-section-label">
                        NOTES
                    </span>

                    <p>
                        {experiment.notes}
                    </p>
                </div>
            )}

            <div className="experiment-detail-section">

                <div className="detail-section-heading">
                    <div>
                        <span className="section-eyebrow">
                            RESEARCH DEFINITION
                        </span>

                        <h2>
                            Configuration
                        </h2>
                    </div>
                </div>

                <ExperimentConfig
                    config={researchConfig}
                />

            </div>

            <div className="experiment-detail-section">

                <div className="detail-section-heading">
                    <div>
                        <span className="section-eyebrow">
                            RESEARCH OUTCOME
                        </span>

                        <h2>
                            Training Results
                        </h2>
                    </div>
                </div>

                <ExperimentPerformance
                    result={researchResult}
                />

            </div>

            {isLocked && (
                <div className="experiment-detail-section strategy-promotion-section">

                    <div className="detail-section-heading">
                        <div>
                            <span className="section-eyebrow">
                                STRATEGY LIFECYCLE
                            </span>

                            <h2>
                                Promote Experiment
                            </h2>
                        </div>
                    </div>

                    {!createdStrategy ? (
                        <div className="strategy-promotion-card">

                            <div className="strategy-promotion-intro">
                                <strong>
                                    Create a strategy from this locked experiment
                                </strong>

                                <p>
                                    The research configuration will be
                                    captured as Strategy v1. The strategy
                                    starts in DRAFT status.
                                </p>
                            </div>

                            <div className="strategy-form">

                                <div className="strategy-form-field">
                                    <label>
                                        STRATEGY NAME
                                    </label>

                                    <input
                                        type="text"
                                        value={strategyName}
                                        onChange={(event) =>
                                            setStrategyName(
                                                event.target.value
                                            )
                                        }
                                        placeholder="e.g. RSI Oversold BTST"
                                    />
                                </div>

                                <div className="strategy-form-field">
                                    <label>
                                        DESCRIPTION
                                    </label>

                                    <textarea
                                        value={strategyDescription}
                                        onChange={(event) =>
                                            setStrategyDescription(
                                                event.target.value
                                            )
                                        }
                                        placeholder="Optional strategy description..."
                                        rows={3}
                                    />
                                </div>

                                <div className="strategy-form-field">
                                    <label>
                                        VERSION NOTES
                                    </label>

                                    <textarea
                                        value={versionNotes}
                                        onChange={(event) =>
                                            setVersionNotes(
                                                event.target.value
                                            )
                                        }
                                        placeholder="Optional notes about this strategy version..."
                                        rows={3}
                                    />
                                </div>

                                {strategyError && (
                                    <div className="strategy-form-error">
                                        {strategyError}
                                    </div>
                                )}

                                <div className="strategy-form-actions">
                                    <button
                                        className="strategy-create-button"
                                        onClick={createStrategy}
                                        disabled={isCreatingStrategy}
                                    >
                                        {isCreatingStrategy
                                            ? 'CREATING...'
                                            : 'CREATE STRATEGY'}
                                    </button>
                                </div>

                            </div>

                        </div>
                    ) : (
                        <div className="strategy-created-card">

                            <div className="strategy-created-header">
                                <div>
                                    <span className="section-eyebrow">
                                        STRATEGY CREATED
                                    </span>

                                    <h3>
                                        {createdStrategy.strategy_name}
                                    </h3>
                                </div>

                                <span className="strategy-status-badge">
                                    {createdStrategy.status}
                                </span>
                            </div>

                            <div className="strategy-created-grid">

                                <div>
                                    <span>STRATEGY SLUG</span>
                                    <strong>
                                        {createdStrategy.strategy_slug}
                                    </strong>
                                </div>

                                <div>
                                    <span>VERSION</span>
                                    <strong>
                                        v{createdStrategy.version}
                                    </strong>
                                </div>

                                <div>
                                    <span>SOURCE EXPERIMENT</span>
                                    <strong>
                                        {createdStrategy.source_experiment_id}
                                    </strong>
                                </div>

                                <div>
                                    <span>CREATED</span>
                                    <strong>
                                        {formatDate(
                                            createdStrategy.created_at
                                        )}
                                    </strong>
                                </div>

                            </div>

                            <div className="strategy-created-message">
                                Strategy v{createdStrategy.version} has been
                                created in DRAFT status.
                            </div>

                        </div>
                    )}

                </div>
            )}

        </section>
    )
}

export default ExperimentDetail