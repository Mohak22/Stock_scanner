import ExperimentStatus from './ExperimentStatus'

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

function ExperimentTable({ experiments, onOpen, onDelete }) {
    if (experiments.length === 0) {
        return (
            <div className="experiment-empty">
                <div className="experiment-empty-icon">◎</div>
                <h3>No experiments found</h3>
                <p>
                    Saved research experiments will appear here.
                </p>
            </div>
        )
    }

    return (
        <div className="experiment-table-wrapper">
            <table className="experiment-table">
                <thead>
                    <tr>
                        <th>Experiment</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th>Tags</th>
                        <th></th>
                    </tr>
                </thead>

                <tbody>
                    {experiments.map((experiment) => (
                        <tr key={experiment.experiment_id}>
                            <td>
                                <div className="experiment-name">
                                    {experiment.name || 'Untitled Experiment'}
                                </div>

                                <div className="experiment-id">
                                    {experiment.experiment_id}
                                </div>
                            </td>

                            <td>
                                <ExperimentStatus
                                    status={experiment.status}
                                />
                            </td>

                            <td>
                                <span className="experiment-date">
                                    {formatDate(experiment.created_at)}
                                </span>
                            </td>

                            <td>
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
                                        <span className="no-tags">—</span>
                                    )}
                                </div>
                            </td>

                            <td>
                                <div className="experiment-actions">
                                    <button
                                        className="experiment-open-button"
                                        onClick={() => onOpen(experiment)}
                                    >
                                        OPEN
                                    </button>

                                    <button
                                        className="experiment-delete-button"
                                        onClick={() => onDelete(experiment)}
                                    >
                                        DELETE
                                    </button>
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

export default ExperimentTable