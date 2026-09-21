import { useEffect, useMemo, useState } from 'react'
import ExperimentFilters from './ExperimentFilters'
import ExperimentTable from './ExperimentTable'

const API_BASE = 'http://127.0.0.1:8000'

function ExperimentHistory({ onOpenExperiment }) {
    const [experiments, setExperiments] = useState([])
    const [search, setSearch] = useState('')
    const [statusFilter, setStatusFilter] = useState('ALL')

    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState('')

    useEffect(() => {
        let cancelled = false

        async function loadExperiments() {
            try {
                setIsLoading(true)
                setError('')

                const response = await fetch(
                    `${API_BASE}/research/experiments`
                )

                if (!response.ok) {
                    throw new Error(
                        `Failed to load experiments (${response.status})`
                    )
                }

                const data = await response.json()

                if (!cancelled) {
                    setExperiments(data.experiments || [])
                }
            } catch (err) {
                if (!cancelled) {
                    setError(
                        err.message || 'Failed to load experiments.'
                    )
                }
            } finally {
                if (!cancelled) {
                    setIsLoading(false)
                }
            }
        }

        loadExperiments()

        return () => {
            cancelled = true
        }
    }, [])

    const filteredExperiments = useMemo(() => {
        const query = search.trim().toLowerCase()

        return experiments.filter((experiment) => {
            const matchesStatus =
                statusFilter === 'ALL' ||
                experiment.status === statusFilter

            if (!matchesStatus) {
                return false
            }

            if (!query) {
                return true
            }

            const searchableText = [
                experiment.name,
                experiment.experiment_id,
                ...(experiment.tags || []),
            ]
                .filter(Boolean)
                .join(' ')
                .toLowerCase()

            return searchableText.includes(query)
        })
    }, [experiments, search, statusFilter])

    async function handleDelete(experiment) {
        const confirmed = window.confirm(
            `Delete "${experiment.name || experiment.experiment_id}"?\n\nThis permanently removes the saved experiment from the research data repository.`
        )

        if (!confirmed) {
            return
        }

        try {
            setError('')

            const response = await fetch(
                `${API_BASE}/research/experiments/${experiment.experiment_id}`,
                {
                    method: 'DELETE',
                }
            )

            if (!response.ok) {
                const data = await response.json().catch(() => null)

                throw new Error(
                    data?.detail ||
                    `Failed to delete experiment (${response.status})`
                )
            }

            setExperiments((current) =>
                current.filter(
                    (item) =>
                        item.experiment_id !==
                        experiment.experiment_id
                )
            )
        } catch (err) {
            setError(
                err.message ||
                'Failed to delete experiment.'
            )
        }
    }

    function handleOpen(experiment) {
        if (onOpenExperiment) {
            onOpenExperiment(experiment)
        }
    }

    return (
        <section className="experiment-history">
            <div className="experiment-page-header">
                <div>
                    <div className="section-eyebrow">
                        RESEARCH WORKSPACE
                    </div>

                    <h1>Experiment History</h1>

                    <p>
                        Review, preserve and manage your research experiments.
                    </p>
                </div>

                <div className="experiment-count">
                    <span>{filteredExperiments.length}</span>
                    <small>EXPERIMENTS</small>
                </div>
            </div>

            <div className="experiment-toolbar">
                <ExperimentFilters
                    search={search}
                    setSearch={setSearch}
                    statusFilter={statusFilter}
                    setStatusFilter={setStatusFilter}
                />
            </div>

            {isLoading && (
                <div className="experiment-state">
                    Loading experiments...
                </div>
            )}

            {!isLoading && error && (
                <div className="experiment-state experiment-error">
                    <strong>Unable to load experiments</strong>
                    <span>{error}</span>
                </div>
            )}

            {!isLoading && !error && (
                <ExperimentTable
                    experiments={filteredExperiments}
                    onOpen={handleOpen}
                    onDelete={handleDelete}
                />
            )}
        </section>
    )
}

export default ExperimentHistory