function TopBar() {
  return (
    <header className="topbar">

      <div className="topbar-left">
        <div className="page-label">
          RESEARCH WORKSTATION
        </div>

        <div className="market-status">
          <span className="status-dot"></span>
          MARKET OPEN
        </div>
      </div>

      <div className="topbar-right">

        <div className="topbar-market">
          <span>NIFTY 50</span>
          <strong>24,850.35</strong>
          <small>+0.72%</small>
        </div>

        <div className="topbar-market">
          <span>NIFTY BANK</span>
          <strong>54,210.10</strong>
          <small>+0.41%</small>
        </div>

        <button className="theme-button">
          ◐
        </button>

        <div className="user-profile">
          <div className="user-avatar">M</div>

          <div>
            <strong>Researcher</strong>
            <span>Personal Workspace</span>
          </div>
        </div>

      </div>

    </header>
  )
}

export default TopBar