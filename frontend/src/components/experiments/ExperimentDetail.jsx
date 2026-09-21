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

        </section>
    )
}

export default ExperimentDetail