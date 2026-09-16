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
            Combine technical and market features to define your hypothesis.
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

      {conditions.map((condition) => {
        const featureDefinition = getFeatureDefinition(condition.feature)
        const hasParameter = featureDefinition?.parameters?.length > 0
        const parameter = featureDefinition?.parameters?.[0]

        return (
          <div className="condition-row" key={condition.id}>
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
                onUpdateCondition(condition.id, 'operator', event.target.value)
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
              value={condition.value}
              onChange={(event) =>
                onUpdateCondition(condition.id, 'value', event.target.value)
              }
              disabled={isRunning}
            />

            <button
              className="remove-condition"
              onClick={() => onRemoveCondition(condition.id)}
              disabled={isRunning || conditions.length === 1}
            >
              ×
            </button>
          </div>
        )
      })}
    </div>
  )
}

export default ConditionBuilder
