function formatNumber(value, suffix = '') {
    if (
        value === null ||
        value === undefined ||
        Number.isNaN(Number(value))
    ) {
        return '—'
    }

    return `${Number(value).toFixed(2)}${suffix}`
}

function ExperimentPerformance({ result }) {
    const training = result?.training || {}
    const summary = training.summary || {}
    const performance = training.performance || {}

    const horizons = Object.keys(performance)

    return (
        <div className="experiment-performance">

            <div className="experiment-summary-grid">

                <div className="experiment-summary-card">
                    <span>Signals</span>
                    <strong>
                        {summary.signal_count ?? '—'}
                    </strong>
                </div>

                <div className="experiment-summary-card">
                    <span>Signal Rate</span>
                    <strong>
                        {formatNumber(
                            summary.signal_rate,
                            '%'
                        )}
                    </strong>
                </div>

                <div className="experiment-summary-card">
                    <span>Stocks With Signals</span>
                    <strong>
                        {summary.stocks_with_signals ?? '—'}
                    </strong>
                </div>

                <div className="experiment-summary-card">
                    <span>Horizons</span>
                    <strong>
                        {horizons.length}
                    </strong>
                </div>

            </div>

            {horizons.length > 0 && (
                <div className="experiment-performance-table-wrapper">
                    <table className="experiment-performance-table">
                        <thead>
                            <tr>
                                <th>HORIZON</th>
                                <th>AVG RETURN</th>
                                <th>MEDIAN</th>
                                <th>POSITIVE</th>
                                <th>OBSERVATIONS</th>
                            </tr>
                        </thead>

                        <tbody>
                            {horizons.map((horizon) => {
                                const data =
                                    performance[horizon]

                                return (
                                    <tr key={horizon}>
                                        <td>
                                            <strong>
                                                {horizon}
                                            </strong>
                                        </td>

                                        <td>
                                            {formatNumber(
                                                data.average_return,
                                                '%'
                                            )}
                                        </td>

                                        <td>
                                            {formatNumber(
                                                data.median_return,
                                                '%'
                                            )}
                                        </td>

                                        <td>
                                            {formatNumber(
                                                data.positive_return_pct,
                                                '%'
                                            )}
                                        </td>

                                        <td>
                                            {data.observations ?? '—'}
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            )}

        </div>
    )
}

export default ExperimentPerformance