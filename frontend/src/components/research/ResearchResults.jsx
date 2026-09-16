import { useState } from 'react'

function ResearchResults({ researchResult }) {
  const [activeAnalysisTab, setActiveAnalysisTab] = useState('stock')

  if (!researchResult) {
    return null
  }

  const training = researchResult.training || {}
  const summary = training.summary || {}
  const diagnostics = training.diagnostics || {}
  const performance = training.performance || {}
  const analysis = training.analysis || {}
  const byStock = analysis.by_stock || {}
  const byFeature = analysis.by_feature || {}
  const byMarketRegime = analysis.by_market_regime || {}

  return (
    <div className="research-results">
      <div className="results-header">
        <div>
          <span className="section-kicker">RESEARCH OUTPUT</span>
          <h2>Research Completed</h2>
          <p>
            The backend successfully executed the configured research experiment.
          </p>
        </div>

        <div className="research-status success">
          <span className="status-dot"></span>
          COMPLETE
        </div>
      </div>

      <div className="results-grid">
        <div className="result-card">
          <span>Signals</span>
          <strong>{summary.signal_count?.toLocaleString() ?? '—'}</strong>
        </div>

        <div className="result-card">
          <span>Signal Rate</span>
          <strong>
            {summary.signal_rate != null
              ? `${Number(summary.signal_rate).toFixed(2)}%`
              : '—'}
          </strong>
        </div>

        <div className="result-card">
          <span>Stocks With Signals</span>
          <strong>
            {summary.stocks_with_signals?.toLocaleString() ?? '—'}
          </strong>
        </div>

        <div className="result-card">
          <span>Sample Quality</span>
          <strong>{diagnostics.sample_quality?.classification ?? '—'}</strong>
        </div>
      </div>

      <div className="result-section">
        <div className="section-heading">
          <div>
            <span className="section-kicker">PERFORMANCE ANALYSIS</span>
            <h3>Forward Return Performance</h3>
          </div>
          <span className="section-meta">
            {Object.keys(performance).length} horizons evaluated
          </span>
        </div>

        <div className="performance-grid">
          {Object.entries(performance).map(([horizon, metrics]) => (
            <div className="performance-card" key={horizon}>
              <div className="performance-card-header">
                <span className="horizon-label">{horizon}</span>
                <span className="observation-count">
                  {metrics.observations?.toLocaleString() ?? '—'} observations
                </span>
              </div>

              <div className="primary-performance">
                <span>Average Return</span>
                <strong
                  className={
                    metrics.average_return >= 0
                      ? 'positive-value'
                      : 'negative-value'
                  }
                >
                  {metrics.average_return != null
                    ? `${metrics.average_return.toFixed(2)}%`
                    : '—'}
                </strong>
              </div>

              <div className="performance-metrics">
                <div>
                  <span>Median</span>
                  <strong>{metrics.median_return?.toFixed(2) ?? '—'}%</strong>
                </div>
                <div>
                  <span>Positive</span>
                  <strong>{metrics.positive_return_pct?.toFixed(2) ?? '—'}%</strong>
                </div>
                <div>
                  <span>Excess vs NIFTY</span>
                  <strong
                    className={
                      metrics.average_excess_return >= 0
                        ? 'positive-value'
                        : 'negative-value'
                    }
                  >
                    {metrics.average_excess_return?.toFixed(2) ?? '—'}%
                  </strong>
                </div>
                <div>
                  <span>Outperformed</span>
                  <strong>
                    {metrics.outperformed_market_pct?.toFixed(2) ?? '—'}%
                  </strong>
                </div>
                <div>
                  <span>Best</span>
                  <strong className="positive-value">
                    {metrics.best_return?.toFixed(2) ?? '—'}%
                  </strong>
                </div>
                <div>
                  <span>Worst</span>
                  <strong className="negative-value">
                    {metrics.worst_return?.toFixed(2) ?? '—'}%
                  </strong>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="performance-table-wrapper">
          <table className="performance-table">
            <thead>
              <tr>
                <th>Horizon</th>
                <th>Avg Return</th>
                <th>Median</th>
                <th>Positive</th>
                <th>Avg NIFTY</th>
                <th>Excess Return</th>
                <th>Outperformed</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(performance).map(([horizon, metrics]) => (
                <tr key={horizon}>
                  <td className="table-horizon">{horizon}</td>
                  <td className={metrics.average_return >= 0 ? 'positive-value' : 'negative-value'}>
                    {metrics.average_return?.toFixed(2) ?? '—'}%
                  </td>
                  <td>{metrics.median_return?.toFixed(2) ?? '—'}%</td>
                  <td>{metrics.positive_return_pct?.toFixed(2) ?? '—'}%</td>
                  <td>{metrics.average_market_return?.toFixed(2) ?? '—'}%</td>
                  <td className={metrics.average_excess_return >= 0 ? 'positive-value' : 'negative-value'}>
                    {metrics.average_excess_return?.toFixed(2) ?? '—'}%
                  </td>
                  <td>{metrics.outperformed_market_pct?.toFixed(2) ?? '—'}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="analysis-section">
        <div className="analysis-header">
          <div>
            <span className="section-kicker">RESEARCH INTELLIGENCE</span>
            <h3>Signal Analysis</h3>
            <p>
              Decompose the research result across stocks, features and market regimes.
            </p>
          </div>
          <div className="analysis-live-indicator">
            <span className="analysis-pulse"></span>
            ANALYSIS READY
          </div>
        </div>

        <div className="analysis-tabs">
          <button className={`analysis-tab ${activeAnalysisTab === 'stock' ? 'active' : ''}`} onClick={() => setActiveAnalysisTab('stock')}>
            <span className="tab-number">01</span>
            <span><strong>By Stock</strong><small>Stock-level behaviour</small></span>
          </button>
          <button className={`analysis-tab ${activeAnalysisTab === 'feature' ? 'active' : ''}`} onClick={() => setActiveAnalysisTab('feature')}>
            <span className="tab-number">02</span>
            <span><strong>By Feature</strong><small>Feature effectiveness</small></span>
          </button>
          <button className={`analysis-tab ${activeAnalysisTab === 'regime' ? 'active' : ''}`} onClick={() => setActiveAnalysisTab('regime')}>
            <span className="tab-number">03</span>
            <span><strong>Market Regime</strong><small>Contextual behaviour</small></span>
          </button>
        </div>

        {activeAnalysisTab === 'stock' && (
          <div className="analysis-panel">
            <div className="analysis-panel-top">
              <div>
                <span className="panel-kicker">STOCK ATTRIBUTION</span>
                <h4>Performance by Stock</h4>
              </div>
              <div className="stock-analysis-summary">
                <span>{Object.keys(byStock).length}</span> stocks analysed
              </div>
            </div>

            <div className="stock-table-wrapper">
              <table className="stock-analysis-table">
                <thead>
                  <tr><th>Stock</th><th>Signals</th><th>T+1</th><th>T+3</th><th>T+5</th><th>T+10</th></tr>
                </thead>
                <tbody>
                  {Object.entries(byStock).slice(0, 100).map(([symbol, stock]) => (
                    <tr key={symbol}>
                      <td><div className="stock-symbol"><span className="stock-icon">◈</span><strong>{symbol}</strong></div></td>
                      <td className="signal-count">{stock.signal_count?.toLocaleString() ?? '—'}</td>
                      {[1, 3, 5, 10].map((horizon) => {
                        const metrics = stock.performance?.[`T+${horizon}`]
                        return (
                          <td key={horizon} className={metrics?.average_return >= 0 ? 'positive-value' : 'negative-value'}>
                            {metrics?.average_return != null ? `${metrics.average_return.toFixed(2)}%` : '—'}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {Object.keys(byStock).length > 100 && (
              <div className="table-footer">Showing first 100 stocks from {Object.keys(byStock).length.toLocaleString()} analysed.</div>
            )}
          </div>
        )}

        {activeAnalysisTab === 'feature' && (
          <div className="analysis-panel">
            <div className="analysis-panel-top">
              <div><span className="panel-kicker">FEATURE ATTRIBUTION</span><h4>Performance by Feature</h4></div>
              <div className="feature-intelligence">FEATURE → OUTCOME</div>
            </div>
            <div className="feature-analysis-grid">
              {Object.entries(byFeature).map(([feature, data]) => {
                const buckets = data?.buckets || {}
                return (
                  <div className="feature-analysis-card" key={feature}>
                    <div className="feature-card-top">
                      <div className="feature-symbol">ƒx</div>
                      <div><strong>{feature}</strong><span>Observed signal distribution</span></div>
                    </div>
                    <div className="feature-card-body">
                      {Object.entries(buckets).map(([bucket, bucketData]) => {
                        const result = bucketData?.performance?.['T+5']
                        return (
                          <div className="feature-bucket" key={bucket}>
                            <div className="bucket-label"><span>{bucket}</span><strong>{bucketData?.signal_count?.toLocaleString?.() ?? '—'}</strong></div>
                            <div className="bucket-bar"><div style={{ width: `${Math.min(Math.max(result?.positive_return_pct || 0, 0), 100)}%` }} /></div>
                            <span className="bucket-result">{result?.average_return != null ? `${result.average_return.toFixed(2)}% avg` : '—'}</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
              {Object.keys(byFeature).length === 0 && <div className="empty-analysis">Feature analysis is not available for this research run.</div>}
            </div>
          </div>
        )}

        {activeAnalysisTab === 'regime' && (
          <div className="analysis-panel">
            <div className="analysis-panel-top">
              <div><span className="panel-kicker">MARKET CONTEXT</span><h4>Performance by Market Regime</h4></div>
              <div className="regime-definition">20D NIFTY 50 TRAILING RETURN</div>
            </div>
            <div className="regime-grid">
              {Object.entries(byMarketRegime).map(([regime, data]) => {
                const metrics = data?.performance?.['T+5']
                return (
                  <div className={`regime-card regime-${regime.toLowerCase()}`} key={regime}>
                    <div className="regime-card-header"><div className="regime-orb"></div><div><span className="regime-name">{regime}</span><small>Market environment</small></div></div>
                    <div className="regime-main-metric"><span>Average Return</span><strong>{metrics?.average_return != null ? `${metrics.average_return.toFixed(2)}%` : '—'}</strong></div>
                    <div className="regime-stats"><div><span>Signals</span><strong>{data?.signal_count?.toLocaleString?.() ?? '—'}</strong></div><div><span>Positive</span><strong>{metrics?.positive_return_pct != null ? `${metrics.positive_return_pct.toFixed(1)}%` : '—'}</strong></div></div>
                  </div>
                )
              })}
              {Object.keys(byMarketRegime).length === 0 && <div className="empty-analysis">Market-regime analysis is not available for this research run.</div>}
            </div>
          </div>
        )}
      </div>

      {diagnostics.warnings?.length > 0 && (
        <div className="warnings-card">
          <div className="card-title">Research Warnings</div>
          {diagnostics.warnings.map((warning, index) => (
            <div className="warning-row" key={index}>⚠ {warning}</div>
          ))}
        </div>
      )}

      <details className="raw-result">
        <summary>View Raw Research Response</summary>
        <pre>{JSON.stringify(researchResult, null, 2)}</pre>
      </details>
    </div>
  )
}

export default ResearchResults
