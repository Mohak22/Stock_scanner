
function ConditionBuilder({
  conditions,
  features,
  loadingFeatures,
  featureError,
  isRunning,
  onAddCondition,
  onRemoveCondition,
  onUpdateCondition,
  onUpdateFeature,
}) {
  const featureFor = (id) =>
    features.find((feature) => feature.id === id)

  const update = (id, path, value) =>
    onUpdateCondition(id, path, value)

  const updateParameter = (id, side, parameter, raw) => {
    const type = String(parameter.type || '').toLowerCase()
    const value =
      type === 'integer' || type === 'number' || type === 'float'
        ? raw === '' ? '' : Number(raw)
        : raw
    update(id, `${side}.parameters.${parameter.id}`, value)
  }

  const renderParameters = (condition, side, definition) =>
    (definition?.parameters || []).map((parameter) => {
      const value =
        condition[side]?.parameters?.[parameter.id] ??
        parameter.default ??
        ''
      const type = String(parameter.type || '').toLowerCase()
      return (
        <input
          key={parameter.id}
          className="period-input"
          type={type === 'integer' || type === 'number' || type === 'float' ? 'number' : 'text'}
          min={parameter.minimum}
          max={parameter.maximum}
          step={type === 'integer' ? '1' : 'any'}
          value={value}
          placeholder={parameter.name}
          aria-label={parameter.name}
          title={parameter.description || parameter.name}
          onChange={(event) =>
            updateParameter(condition.id, side, parameter, event.target.value)
          }
          disabled={isRunning}
        />
      )
    })

  return (
    <div className="conditions-section">
      <div className="conditions-header">
        <div>
          <label>Research Conditions</label>
          <span>Build rules from registry-defined indicators and parameters.</span>
        </div>
        <button
          className="secondary-button"
          onClick={onAddCondition}
          disabled={isRunning || loadingFeatures || features.length === 0}
        >
          + Add Condition
        </button>
      </div>

      {loadingFeatures && <div className="indicator-status">Loading indicators...</div>}
      {!loadingFeatures && featureError && (
        <div className="indicator-status error">{featureError}</div>
      )}

      {!loadingFeatures && !featureError && conditions.map((condition, index) => {
        const left = condition.left || {}
        const right = condition.right || {}
        const leftDef = featureFor(left.feature)
        const rightDef = featureFor(right.feature)
        const rightType = right.feature ? 'feature' : 'value'

        return (
          <div key={condition.id}>
            {index > 0 && (
              <div className="condition-logic"><span /><strong>AND</strong><span /></div>
            )}

            <div className="condition-card">
              <div className="condition-card-header">
                <div>
                  <span className="condition-number">CONDITION {index + 1}</span>
                  <span className="condition-description">Define a rule for selecting stocks</span>
                </div>
                <button
                  className="remove-condition"
                  onClick={() => onRemoveCondition(condition.id)}
                  disabled={isRunning || conditions.length === 1}
                  title="Remove condition"
                >
                  ×
                </button>
              </div>

              <div className="condition-builder-row">
                <div className="rule-group">
                  <span className="rule-label">Indicator</span>
                  <div className="rule-controls">
                    <select
                      value={left.feature || ''}
                      onChange={(event) =>
                        onUpdateFeature(condition.id, 'left', event.target.value)
                      }
                      disabled={isRunning}
                    >
                      {features.map((feature) => (
                        <option key={feature.id} value={feature.id}>{feature.name}</option>
                      ))}
                    </select>
                    {renderParameters(condition, 'left', leftDef)}
                  </div>
                </div>

                <div className="rule-operator">
                  <span className="rule-label">Compare</span>
                  <select
                    value={condition.operator}
                    onChange={(event) => update(condition.id, 'operator', event.target.value)}
                    disabled={isRunning}
                  >
                    <option value="<">&lt;</option>
                    <option value="<=">&lt;=</option>
                    <option value=">">&gt;</option>
                    <option value=">=">&gt;=</option>
                    <option value="==">==</option>
                    <option value="!=">!=</option>
                  </select>
                </div>

                <div className="rule-group right-rule">
                  <span className="rule-label">Against</span>
                  <div className="rule-controls">
                    <select
                      value={rightType}
                      onChange={(event) => {
                        if (event.target.value === 'feature') {
                          onUpdateFeature(condition.id, 'right', features[0]?.id || '')
                        } else {
                          update(condition.id, 'right', { value: 0, multiplier: 1 })
                        }
                      }}
                      disabled={isRunning}
                    >
                      <option value="value">Fixed Value</option>
                      <option value="feature">Indicator</option>
                    </select>

                    {rightType === 'value' ? (
                      <input
                        className="value-input"
                        type="number"
                        value={right.value ?? ''}
                        placeholder="Value"
                        onChange={(event) => update(condition.id, 'right.value', event.target.value)}
                        disabled={isRunning}
                      />
                    ) : (
                      <>
                        <select
                          value={right.feature || ''}
                          onChange={(event) =>
                            onUpdateFeature(condition.id, 'right', event.target.value)
                          }
                          disabled={isRunning}
                        >
                          {features.map((feature) => (
                            <option key={feature.id} value={feature.id}>{feature.name}</option>
                          ))}
                        </select>
                        {renderParameters(condition, 'right', rightDef)}
                      </>
                    )}
                  </div>
                </div>
              </div>

              <div className="condition-preview">
                <span className="preview-label">RULE</span>
                <span className="preview-expression">
                  {leftDef?.name || left.feature}
                  {leftDef?.parameters?.map((parameter) =>
                    left.parameters?.[parameter.id] != null &&
                    left.parameters?.[parameter.id] !== ''
                      ? <span key={parameter.id}> ({left.parameters[parameter.id]})</span>
                      : null
                  )}
                  <span className="preview-operator"> {condition.operator} </span>
                  {rightType === 'feature'
                    ? <>
                        <strong>{rightDef?.name || right.feature}</strong>
                        {rightDef?.parameters?.map((parameter) =>
                          right.parameters?.[parameter.id] != null &&
                          right.parameters?.[parameter.id] !== ''
                            ? <span key={parameter.id}> ({right.parameters[parameter.id]})</span>
                            : null
                        )}
                      </>
                    : right.value ?? 'Value'}
                </span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default ConditionBuilder
