function ExperimentFilters({
  search,
  setSearch,
  statusFilter,
  setStatusFilter,
}) {
  return (
    <div className="experiment-filters">
      <div className="experiment-search">
        <input
          type="text"
          placeholder="Search experiments..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>

      <select
        value={statusFilter}
        onChange={(event) => setStatusFilter(event.target.value)}
      >
        <option value="ALL">All Status</option>
        <option value="SAVED">Saved</option>
        <option value="LOCKED">Locked</option>
      </select>
    </div>
  )
}

export default ExperimentFilters