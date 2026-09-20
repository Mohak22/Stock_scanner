function ConditionBuilder({
  conditions,
  features,
  isRunning,
  onAddCondition,
  onRemoveCondition,
  onUpdateCondition,
  onUpdateFeature,
}) {
  const getFeatureDefinition = (featureId) =>
    features.find((feature) => feature.id === featureId)

  return (
    <div className="conditions-section">
      <div className="conditions-header">
        <div>
          <label>Research Conditions</label>
          <span>
            Define the conditions that must be satisfied by a stock.
          </span>
        </div>

        <button
          className="secondary-button"
          onClick={onAddCondition}
          disabled={isRunning}
        >
          + Add Condition
        </button>
      </div>

      {conditions.map((condition, index) => {
        const featureDefinition = getFeatureDefinition(condition.feature)
        const parameter = featureDefinition?.parameters?.[0]
        const hasParameter = Boolean(parameter)

        return (
          <div key={condition.id}>
            {index > 0 && (
              <div className="condition-logic">
                AND
              </div>
            )}

            <div className="condition-row">
              <select
                value={condition.feature}
                onChange={(event) =>
                  onUpdateFeature(condition.id, event.target.value)
                }
                disabled={isRunning}
              >
                {features.map((feature) => (
                  <option key={feature.id} value={feature.id}>
                    {feature.name}
                  </option>
                ))}
              </select>

              {hasParameter && (
                <input
                  type="number"
                  min={parameter.minimum}
                  max={parameter.maximum}
                  step="1"
                  title={`${parameter.name}: ${parameter.minimum}–${parameter.maximum}`}
                  value={condition.period ?? ''}
                  onChange={(event) =>
                    onUpdateCondition(
                      condition.id,
                      'period',
                      event.target.value === ''
                        ? ''
                        : Number(event.target.value)
                    )
                  }
                  disabled={isRunning}
                />
              )}

              <select
                value={condition.operator}
                onChange={(event) =>
                  onUpdateCondition(
                    condition.id,
                    'operator',
                    event.target.value
                  )
                }
                disabled={isRunning}
              >
                <option value="<">&lt;</option>
                <option value="<=">&lt;=</option>
                <option value=">">&gt;</option>
                <option value=">=">&gt;=</option>
                <option value="==">==</option>
                <option value="!=">!=</option>
              </select>

              <input
                type="number"
                value={condition.value ?? ''}
                placeholder="Value"
                onChange={(event) =>
                  onUpdateCondition(
                    condition.id,
                    'value',
                    event.target.value
                  )
                }
                disabled={isRunning}
              />

              <button
                className="remove-condition"
                onClick={() => onRemoveCondition(condition.id)}
                disabled={isRunning || conditions.length === 1}
                title="Remove condition"
              >
                ×
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default ConditionBuilder