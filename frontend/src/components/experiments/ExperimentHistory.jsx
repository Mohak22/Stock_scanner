import { useEffect, useMemo, useState } from 'react'
import ExperimentFilters from './ExperimentFilters'
import ExperimentTable from './ExperimentTable'

const API_BASE = 'http://127.0.0.1:8000'

function formatNumber(value, digits = 2) {
    if (
        value === null ||
        value === undefined ||
        value === ''
    ) {
        return '—'
    }

    const number = Number(value)

    if (Number.isNaN(number)) {
        return String(value)
    }

    return number.toFixed(digits)
}

function formatPercent(value) {
    if (
        value === null ||
        value === undefined ||
        value === ''
    ) {
        return '—'
    }

    return `${formatNumber(value)}%`
}

function formatValue(value) {
    if (
        value === null ||
        value === undefined ||
        value === ''
    ) {
        return '—'
    }

    if (Array.isArray(value)) {
        return value.join(', ')
    }

    if (typeof value === 'object') {
        return JSON.stringify(value)
    }

    return String(value)
}

function getPerformance(
    experiment,
    horizon
) {
    return (
        experiment?.development?.performance?.[
        horizon
        ] || null
    )
}

function getConditionText(
    experiment
) {
    const conditions =
        experiment?.research_config?.entry_conditions

    if (!conditions) {
        return '—'
    }

    if (Array.isArray(conditions)) {
        return conditions
            .map((condition) => {

                if (
                    typeof condition !==
                    'object'
                ) {
                    return String(
                        condition
                    )
                }

                const feature =
                    condition.feature ||
                    condition.feature_name ||
                    ''

                const operator =
                    condition.operator ||
                    ''

                const value =
                    condition.value ??
                    ''

                return `${feature} ${operator} ${value}`
            })
            .join(' AND ')
    }

    return formatValue(
        conditions
    )
}

function ExperimentHistory({
    onOpenExperiment,
}) {

    const [experiments, setExperiments] =
        useState([])

    const [search, setSearch] =
        useState('')

    const [statusFilter, setStatusFilter] =
        useState('ALL')

    const [
        selectedExperimentIds,
        setSelectedExperimentIds,
    ] = useState([])

    const [comparison, setComparison] =
        useState(null)

    const [isComparing, setIsComparing] =
        useState(false)

    const [isLoading, setIsLoading] =
        useState(true)

    const [error, setError] =
        useState('')

    useEffect(() => {
        let isMounted = true

        async function fetchExperiments() {
            try {
                const response = await fetch(
                    `${API_BASE}/research/experiments`
                )

                const data = await response.json()

                if (!response.ok) {
                    throw new Error(
                        data?.detail ||
                        `Failed to load experiments (${response.status})`
                    )
                }

                if (isMounted) {
                    setExperiments(data.experiments || [])
                    setError('')
                }
            } catch (err) {
                if (isMounted) {
                    setError(
                        err.message ||
                        'Failed to load experiments.'
                    )
                }
            } finally {
                if (isMounted) {
                    setIsLoading(false)
                }
            }
        }

        fetchExperiments()

        return () => {
            isMounted = false
        }
    }, [])

    const filteredExperiments =
        useMemo(() => {

            const query =
                search
                    .trim()
                    .toLowerCase()

            return experiments.filter(
                (experiment) => {

                    const matchesStatus =
                        statusFilter ===
                        'ALL' ||
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

        setError('')

        setSelectedExperimentIds(
            (current) => {

                if (
                    current.includes(
                        experimentId
                    )
                ) {
                    return current.filter(
                        (id) =>
                            id !==
                            experimentId
                    )
                }

                if (
                    current.length >= 5
                ) {
                    setError(
                        'Maximum 5 experiments can be compared.'
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
        setError('')
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

            const response =
                await fetch(
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
                `Lock "${experiment.name || experiment.experiment_id}"?\n\nThis will preserve the experiment as an immutable research result.`
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
                    `Lock failed (${response.status})`
                )
            }

            if (
                data.status !==
                'LOCKED'
            ) {
                throw new Error(
                    'Backend did not confirm LOCKED status.'
                )
            }

            // Immediately update the visible row.
            setExperiments(
                (current) =>
                    current.map(
                        (item) =>
                            item.experiment_id ===
                                experiment.experiment_id
                                ? {
                                    ...item,
                                    status: 'LOCKED',
                                    locked_at:
                                        data.locked_at,
                                }
                                : item
                    )
            )

            // Remove it from comparison selection.
            setSelectedExperimentIds(
                (current) =>
                    current.filter(
                        (id) =>
                            id !==
                            experiment.experiment_id
                    )
            )

            // Clear any stale comparison.
            setComparison(null)

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
                `Delete "${experiment.name || experiment.experiment_id}"?`
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
                    `Delete failed (${response.status})`
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

            setComparison(null)

        } catch (err) {

            setError(
                err.message ||
                'Failed to delete experiment.'
            )
        }
    }

    function handleOpen(
        experiment
    ) {

        if (onOpenExperiment) {
            onOpenExperiment(
                experiment
            )
        }
    }

    return (
        <section className="experiment-history">

            {/* =====================================================
                HEADER
            ===================================================== */}

            <div className="experiment-page-header">

                <div>

                    <div className="section-eyebrow">
                        RESEARCH WORKSPACE
                    </div>

                    <h1>
                        Experiment History
                    </h1>

                    <p>
                        Review, compare and preserve research experiments.
                    </p>

                </div>

                <div className="experiment-count">

                    <span>
                        {
                            filteredExperiments.length
                        }
                    </span>

                    <small>
                        EXPERIMENTS
                    </small>

                </div>

            </div>

            {/* =====================================================
                TOOLBAR
            ===================================================== */}

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
                        {
                            selectedExperimentIds.length
                        } selected
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
                            ? 'ANALYSING...'
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

            {/* =====================================================
                ERROR
            ===================================================== */}

            {error && (
                <div className="experiment-state experiment-error">

                    <strong>
                        Research workspace error
                    </strong>

                    <span>
                        {error}
                    </span>

                </div>
            )}

            {/* =====================================================
                HISTORY TABLE
            ===================================================== */}

            {isLoading && (
                <div className="experiment-state">
                    Loading experiments...
                </div>
            )}

            {!isLoading && (
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

            {/* =====================================================
                RESEARCH COMPARISON
            ===================================================== */}

            {comparison && (
                <section className="research-comparison-workspace">

                    <div className="research-comparison-header">

                        <div>

                            <div className="section-eyebrow">
                                RESEARCH COMPARISON
                            </div>

                            <h2>
                                Comparative Research Analysis
                            </h2>

                            <p>
                                Compare research configuration, signal quality and forward-return behaviour across experiments.
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

                    {/* =================================================
                        EXPERIMENT CARDS
                    ================================================= */}

                    <div className="research-comparison-experiments">

                        {comparison.experiments?.map(
                            (experiment) => {

                                const t1 =
                                    getPerformance(
                                        experiment,
                                        'T+1'
                                    )

                                const t3 =
                                    getPerformance(
                                        experiment,
                                        'T+3'
                                    )

                                const t5 =
                                    getPerformance(
                                        experiment,
                                        'T+5'
                                    )

                                const t10 =
                                    getPerformance(
                                        experiment,
                                        'T+10'
                                    )

                                return (
                                    <article
                                        className="research-comparison-experiment"
                                        key={
                                            experiment.experiment_id
                                        }
                                    >

                                        <div className="comparison-experiment-title">

                                            <div>

                                                <span className="comparison-experiment-id">
                                                    {
                                                        experiment.experiment_id
                                                    }
                                                </span>

                                                <h3>
                                                    {experiment.name ||
                                                        'Untitled Experiment'}
                                                </h3>

                                            </div>

                                            <span
                                                className={
                                                    experiment.status ===
                                                        'LOCKED'
                                                        ? 'comparison-status locked'
                                                        : 'comparison-status'
                                                }
                                            >
                                                {
                                                    experiment.status
                                                }
                                            </span>

                                        </div>

                                        {/* Configuration */}

                                        <div className="comparison-config-grid">

                                            <div className="comparison-config-item">

                                                <span>
                                                    RESEARCH QUESTION
                                                </span>

                                                <strong>
                                                    {formatValue(
                                                        experiment
                                                            .research_config
                                                            ?.question
                                                    )}
                                                </strong>

                                            </div>

                                            <div className="comparison-config-item">

                                                <span>
                                                    UNIVERSE
                                                </span>

                                                <strong>
                                                    {formatValue(
                                                        experiment
                                                            .research_config
                                                            ?.universe
                                                    )}
                                                </strong>

                                            </div>

                                            <div className="comparison-config-item">

                                                <span>
                                                    CONDITIONS
                                                </span>

                                                <strong>
                                                    {getConditionText(
                                                        experiment
                                                    )}
                                                </strong>

                                            </div>

                                            <div className="comparison-config-item">

                                                <span>
                                                    HORIZONS
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

                                        {/* Key metrics */}

                                        <div className="comparison-metric-grid">

                                            <div className="comparison-metric-card">

                                                <span>
                                                    SIGNALS
                                                </span>

                                                <strong>
                                                    {formatValue(
                                                        t1?.observations
                                                    )}
                                                </strong>

                                            </div>

                                            <div className="comparison-metric-card">

                                                <span>
                                                    T+1 AVG
                                                </span>

                                                <strong>
                                                    {formatNumber(
                                                        t1?.average_return
                                                    )}
                                                    %
                                                </strong>

                                            </div>

                                            <div className="comparison-metric-card">

                                                <span>
                                                    T+3 AVG
                                                </span>

                                                <strong>
                                                    {formatNumber(
                                                        t3?.average_return
                                                    )}
                                                    %
                                                </strong>

                                            </div>

                                            <div className="comparison-metric-card">

                                                <span>
                                                    T+5 AVG
                                                </span>

                                                <strong>
                                                    {formatNumber(
                                                        t5?.average_return
                                                    )}
                                                    %
                                                </strong>

                                            </div>

                                            <div className="comparison-metric-card">

                                                <span>
                                                    T+10 AVG
                                                </span>

                                                <strong>
                                                    {formatNumber(
                                                        t10?.average_return
                                                    )}
                                                    %
                                                </strong>

                                            </div>

                                        </div>

                                    </article>
                                )
                            }
                        )}

                    </div>

                    {/* =================================================
                        PERFORMANCE MATRIX
                    ================================================= */}

                    <div className="research-comparison-panel">

                        <div className="research-comparison-panel-header">

                            <div>

                                <div className="section-eyebrow">
                                    FORWARD RETURNS
                                </div>

                                <h3>
                                    Development Performance Matrix
                                </h3>

                            </div>

                        </div>

                        <div className="research-comparison-performance-grid">

                            {['T+1', 'T+3', 'T+5', 'T+10'].map(
                                (horizon) => (

                                    <div
                                        className="comparison-horizon-card"
                                        key={
                                            horizon
                                        }
                                    >

                                        <div className="comparison-horizon-title">
                                            {horizon}
                                        </div>

                                        {comparison.experiments?.map(
                                            (experiment) => {

                                                const performance =
                                                    getPerformance(
                                                        experiment,
                                                        horizon
                                                    )

                                                return (
                                                    <div
                                                        className="comparison-performance-row"
                                                        key={
                                                            experiment.experiment_id
                                                        }
                                                    >

                                                        <div className="comparison-performance-name">

                                                            <span>
                                                                {
                                                                    experiment.name ||
                                                                    experiment.experiment_id
                                                                }
                                                            </span>

                                                        </div>

                                                        <div className="comparison-performance-main">

                                                            <strong>
                                                                {formatNumber(
                                                                    performance?.average_return
                                                                )}
                                                                %
                                                            </strong>

                                                            <span>
                                                                avg return
                                                            </span>

                                                        </div>

                                                        <div className="comparison-performance-secondary">

                                                            <span>
                                                                Median
                                                            </span>

                                                            <strong>
                                                                {formatNumber(
                                                                    performance?.median_return
                                                                )}
                                                                %
                                                            </strong>

                                                        </div>

                                                        <div className="comparison-performance-secondary">

                                                            <span>
                                                                Positive
                                                            </span>

                                                            <strong>
                                                                {formatPercent(
                                                                    performance?.positive_return_pct
                                                                )}
                                                            </strong>

                                                        </div>

                                                        <div className="comparison-performance-secondary">

                                                            <span>
                                                                Excess
                                                            </span>

                                                            <strong>
                                                                {formatNumber(
                                                                    performance?.average_excess_return
                                                                )}
                                                                %
                                                            </strong>

                                                        </div>

                                                        <div className="comparison-performance-secondary">

                                                            <span>
                                                                Beat Market
                                                            </span>

                                                            <strong>
                                                                {formatPercent(
                                                                    performance?.outperformed_market_pct
                                                                )}
                                                            </strong>

                                                        </div>

                                                    </div>
                                                )
                                            }
                                        )}

                                    </div>
                                )
                            )}

                        </div>

                    </div>

                </section>
            )}

        </section>
    )
}

export default ExperimentHistory