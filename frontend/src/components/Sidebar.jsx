function Sidebar({ activePage, setActivePage }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">◉</div>

        <div>
          <h2>Stock Scanner</h2>
          <span>Research. Test. Trade Smarter.</span>
        </div>
      </div>

      <nav className="sidebar-menu">
        <div className="menu-item">
          Dashboard
        </div>

        <div className="menu-item">
          Scanner
        </div>

        <div className="menu-item">
          Strategy Inventor
        </div>

        <div
          className={`menu-item ${activePage === 'research' ? 'active' : ''
            }`}
          onClick={() => setActivePage('research')}
        >
          Research Cockpit
        </div>

        <div
          className={`menu-item ${activePage === 'experiments' ? 'active' : ''
            }`}
          onClick={() => setActivePage('experiments')}
        >
          Experiment History
        </div>

        <div
          className={`menu-item ${activePage === 'strategies' ? 'active' : ''
            }`}
          onClick={() => setActivePage('strategies')}
        >
          Strategy Library
        </div>

        <div className="menu-item">
          Live Trading
        </div>

        <div className="menu-item">
          Portfolio
        </div>

        <div className="menu-item">
          Watchlist
        </div>

        <div className="menu-item">
          Market Overview
        </div>

        <div className="menu-item">
          Settings
        </div>
      </nav>

      <div className="market-snapshot">
        <h3>Market Snapshot</h3>

        <div className="market-row">
          <span>NIFTY 50</span>
          <span>+0.72%</span>
        </div>

        <div className="market-row">
          <span>NIFTY BANK</span>
          <span>+0.41%</span>
        </div>

        <div className="market-row">
          <span>NIFTY MIDCAP</span>
          <span>+1.06%</span>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar