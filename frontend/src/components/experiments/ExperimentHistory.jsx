import { useEffect, useMemo, useState } from 'react'
import ExperimentFilters from './ExperimentFilters'
import ExperimentTable from './ExperimentTable'

const API_BASE = 'http://127.0.0.1:8000'

function formatValue(value) {
    if (
        value === null ||
        value === undefined ||
        value === ''
    ) {
        return '—'
    }

    if (typeof value === 'object') {
        return JSON.stringify(value)
    }

    return String(value)
}

function extractPerformance(performance) {
    if (!performance || typeof performance !== 'object') {
        return []
    }

    return Object.entries(performance).map(
        ([horizon, value]) => ({
            horizon,
            value,
        })
    )
}

function ExperimentHistory({
    onOpenExperiment,
}) {
    const [experiments, setExperiments] = useState([])

    const [search, setSearch] = useState('')

    const [statusFilter, setStatusFilter] =
        useState('ALL')

    const [selectedExperimentIds, setSelectedExperimentIds] =
        useState([])

    const [comparison, setComparison] =
        useState(null)

    const [isComparing, setIsComparing] =
        useState(false)

    const [isLoading, setIsLoading] =
        useState(true)

    const [error, setError] =
        useState('')

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

            setExperiments(
                data.experiments || []
            )

        } catch (err) {

            setError(
                err.message ||
                'Failed to load experiments.'
            )

        } finally {

            setIsLoading(false)
        }
    }

    useEffect(() => {
        loadExperiments()
    }, [])

    const filteredExperiments = useMemo(() => {

        const query =
            search.trim().toLowerCase()

        return experiments.filter(
            (experiment) => {

                const matchesStatus =
                    statusFilter === 'ALL' ||
                    experiment.status ===
                        statusFilter

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

                return searchableText.includes(
                    query
                )
            }
        )

    }, [
        experiments,
        search,
        statusFilter,
    ])

    function handleToggleSelect(
        experimentId
    ) {

        setSelectedExperimentIds(
            (current) => {

                if (
                    current.includes(
                        experimentId
                    )
                ) {
                    return current.filter(
                        (id) =>
                            id !== experimentId
                    )
                }

                if (current.length >= 5) {
                    setError(
                        'You can compare up to 5 experiments.'
                    )

                    return current
                }

                return [
                    ...current,
                    experimentId,
                ]
            }
        )
    }

    function clearSelection() {
        setSelectedExperimentIds([])
        setComparison(null)
    }

    async function handleCompare() {

        if (
            selectedExperimentIds.length <
            2
        ) {
            setError(
                'Select at least 2 experiments to compare.'
            )

            return
        }

        try {

            setIsComparing(true)
            setError('')

            const response = await fetch(
                `${API_BASE}/research/experiments/compare`,
                {
                    method: 'POST',

                    headers: {
                        'Content-Type':
                            'application/json',
                    },

                    body: JSON.stringify({
                        experiment_ids:
                            selectedExperimentIds,
                    }),
                }
            )

            const data =
                await response.json()

            if (!response.ok) {
                throw new Error(
                    data?.detail ||
                    `Comparison failed (${response.status})`
                )
            }

            setComparison(data)

        } catch (err) {

            setError(
                err.message ||
                'Failed to compare experiments.'
            )

        } finally {

            setIsComparing(false)
        }
    }

    async function handleLock(
        experiment
    ) {

        const confirmed =
            window.confirm(
                `Lock "${experiment.name || experiment.experiment_id}"?\n\nA locked experiment becomes immutable and can later be promoted to a strategy.`
            )

        if (!confirmed) {
            return
        }

        try {

            setError('')

            const response =
                await fetch(
                    `${API_BASE}/research/experiments/${experiment.experiment_id}/lock`,
                    {
                        method: 'POST',
                    }
                )

            const data =
                await response.json()

            if (!response.ok) {
                throw new Error(
                    data?.detail ||
                    `Failed to lock experiment (${response.status})`
                )
            }

            await loadExperiments()

            setSelectedExperimentIds(
                (current) =>
                    current.filter(
                        (id) =>
                            id !==
                            experiment.experiment_id
                    )
            )

        } catch (err) {

            setError(
                err.message ||
                'Failed to lock experiment.'
            )
        }
    }

    async function handleDelete(
        experiment
    ) {

        const confirmed =
            window.confirm(
                `Delete "${experiment.name || experiment.experiment_id}"?\n\nThis permanently removes the saved experiment.`
            )

        if (!confirmed) {
            return
        }

        try {

            setError('')

            const response =
                await fetch(
                    `${API_BASE}/research/experiments/${experiment.experiment_id}`,
                    {
                        method: 'DELETE',
                    }
                )

            const data =
                await response.json()
                    .catch(() => null)

            if (!response.ok) {
                throw new Error(
                    data?.detail ||
                    `Failed to delete experiment (${response.status})`
                )
            }

            setExperiments(
                (current) =>
                    current.filter(
                        (item) =>
                            item.experiment_id !==
                            experiment.experiment_id
                    )
            )

            setSelectedExperimentIds(
                (current) =>
                    current.filter(
                        (id) =>
                            id !==
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

                    <h1>
                        Experiment History
                    </h1>

                    <p>
                        Review, compare, preserve and manage your research experiments.
                    </p>

                </div>

                <div className="experiment-count">

                    <span>
                        {filteredExperiments.length}
                    </span>

                    <small>
                        EXPERIMENTS
                    </small>

                </div>

            </div>

            <div className="experiment-toolbar">

                <ExperimentFilters
                    search={search}
                    setSearch={setSearch}
                    statusFilter={
                        statusFilter
                    }
                    setStatusFilter={
                        setStatusFilter
                    }
                />

                <div className="experiment-selection-toolbar">

                    <span>
                        {selectedExperimentIds.length}{' '}
                        selected
                    </span>

                    <button
                        className="experiment-compare-button"
                        disabled={
                            selectedExperimentIds.length <
                                2 ||
                            isComparing
                        }
                        onClick={
                            handleCompare
                        }
                    >
                        {isComparing
                            ? 'COMPARING...'
                            : 'COMPARE'}
                    </button>

                    {selectedExperimentIds.length >
                        0 && (
                        <button
                            className="experiment-clear-button"
                            onClick={
                                clearSelection
                            }
                        >
                            CLEAR
                        </button>
                    )}

                </div>

            </div>

            {isLoading && (
                <div className="experiment-state">
                    Loading experiments...
                </div>
            )}

            {!isLoading && error && (
                <div className="experiment-state experiment-error">
                    <strong>
                        Experiment workspace error
                    </strong>

                    <span>
                        {error}
                    </span>
                </div>
            )}

            {!isLoading &&
                !error && (
                    <ExperimentTable
                        experiments={
                            filteredExperiments
                        }
                        onOpen={
                            handleOpen
                        }
                        onDelete={
                            handleDelete
                        }
                        onLock={
                            handleLock
                        }
                        selectedExperimentIds={
                            selectedExperimentIds
                        }
                        onToggleSelect={
                            handleToggleSelect
                        }
                    />
                )}

            {comparison && (
                <div className="experiment-comparison">

                    <div className="comparison-header">

                        <div>
                            <div className="section-eyebrow">
                                RESEARCH ANALYSIS
                            </div>

                            <h2>
                                Experiment Comparison
                            </h2>

                            <p>
                                Comparing{' '}
                                {
                                    comparison.experiments
                                        ?.length || 0
                                }{' '}
                                selected experiments.
                            </p>
                        </div>

                        <button
                            className="experiment-clear-button"
                            onClick={() =>
                                setComparison(
                                    null
                                )
                            }
                        >
                            CLOSE
                        </button>

                    </div>

                    <div className="comparison-grid">

                        {(
                            comparison.experiments ||
                            []
                        ).map(
                            (experiment) => {

                                const trainingPerformance =
                                    extractPerformance(
                                        experiment
                                            .training
                                            ?.performance
                                    )

                                return (
                                    <div
                                        className="comparison-card"
                                        key={
                                            experiment.experiment_id
                                        }
                                    >

                                        <div className="comparison-card-header">

                                            <div>

                                                <h3>
                                                    {experiment.name ||
                                                        'Untitled Experiment'}
                                                </h3>

                                                <span>
                                                    {
                                                        experiment.experiment_id
                                                    }
                                                </span>

                                            </div>

                                            <span className="comparison-status">
                                                {
                                                    experiment.status
                                                }
                                            </span>

                                        </div>

                                        <div className="comparison-section">

                                            <h4>
                                                Configuration
                                            </h4>

                                            <div className="comparison-row">
                                                <span>
                                                    Question
                                                </span>

                                                <strong>
                                                    {formatValue(
                                                        experiment
                                                            .research_config
                                                            ?.question
                                                    )}
                                                </strong>
                                            </div>

                                            <div className="comparison-row">
                                                <span>
                                                    Universe
                                                </span>

                                                <strong>
                                                    {formatValue(
                                                        experiment
                                                            .research_config
                                                            ?.universe
                                                    )}
                                                </strong>
                                            </div>

                                            <div className="comparison-row">
                                                <span>
                                                    Date Range
                                                </span>

                                                <strong>
                                                    {formatValue(
                                                        experiment
                                                            .research_config
                                                            ?.date_range
                                                    )}
                                                </strong>
                                            </div>

                                            <div className="comparison-row">
                                                <span>
                                                    Conditions
                                                </span>

                                                <strong>
                                                    {formatValue(
                                                        experiment
                                                            .research_config
                                                            ?.conditions
                                                    )}
                                                </strong>
                                            </div>

                                            <div className="comparison-row">
                                                <span>
                                                    Horizons
                                                </span>

                                                <strong>
                                                    {formatValue(
                                                        experiment
                                                            .research_config
                                                            ?.evaluation_horizons
                                                    )}
                                                </strong>
                                            </div>

                                        </div>

                                        <div className="comparison-section">

                                            <h4>
                                                Training Performance
                                            </h4>

                                            {trainingPerformance.length >
                                            0 ? (
                                                trainingPerformance.map(
                                                    ({
                                                        horizon,
                                                        value,
                                                    }) => (
                                                        <div
                                                            className="comparison-row"
                                                            key={
                                                                horizon
                                                            }
                                                        >
                                                            <span>
                                                                {
                                                                    horizon
                                                                }
                                                            </span>

                                                            <strong>
                                                                {formatValue(
                                                                    value
                                                                )}
                                                            </strong>
                                                        </div>
                                                    )
                                                )
                                            ) : (
                                                <div className="comparison-empty">
                                                    No performance data available.
                                                </div>
                                            )}

                                        </div>

                                    </div>
                                )
                            }
                        )}

                    </div>

                </div>
            )}

        </section>
    )
}

export default ExperimentHistory