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
  const getFeatureDefinition = (featureId) =>
    features.find(
      (feature) => feature.id === featureId
    )

  const updateField = (
    id,
    field,
    value
  ) => {
    onUpdateCondition(
      id,
      field,
      value
    )
  }

  return (
    <div className="conditions-section">
      {/* HEADER */}

      <div className="conditions-header">
        <div>
          <label>
            Research Conditions
          </label>

          <span>
            Build your research logic using
            indicators, comparisons and arithmetic.
          </span>
        </div>

        <button
          className="secondary-button"
          onClick={onAddCondition}
          disabled={
            isRunning ||
            loadingFeatures ||
            features.length === 0
          }
        >
          + Add Condition
        </button>
      </div>

      {/* STATUS */}

      {loadingFeatures && (
        <div className="indicator-status">
          Loading indicators...
        </div>
      )}

      {!loadingFeatures &&
        featureError && (
          <div className="indicator-status error">
            {featureError}
          </div>
        )}

      {!loadingFeatures &&
        !featureError &&
        features.length === 0 && (
          <div className="indicator-status error">
            No indicators are available.
          </div>
        )}

      {/* CONDITIONS */}

      {!loadingFeatures &&
        !featureError &&
        conditions.map(
          (condition, index) => {
            const leftFeature =
              getFeatureDefinition(
                condition.feature
              )

            const leftParameter =
              leftFeature?.parameters?.[0]

            const rightFeature =
              getFeatureDefinition(
                condition.rightFeature
              )

            const rightParameter =
              rightFeature?.parameters?.[0]

            const rightType =
              condition.rightType ||
              'value'

            const multiplier =
              condition.rightMultiplier ??
              1

            return (
              <div key={condition.id}>
                {/* AND */}

                {index > 0 && (
                  <div className="condition-logic">
                    <span></span>
                    <strong>AND</strong>
                    <span></span>
                  </div>
                )}

                {/* CARD */}

                <div className="condition-card">
                  {/* CARD HEADER */}

                  <div className="condition-card-header">
                    <div>
                      <span className="condition-number">
                        CONDITION {index + 1}
                      </span>

                      <span className="condition-description">
                        Define a rule for selecting stocks
                      </span>
                    </div>

                    <button
                      className="remove-condition"
                      onClick={() =>
                        onRemoveCondition(
                          condition.id
                        )
                      }
                      disabled={
                        isRunning ||
                        conditions.length === 1
                      }
                      title="Remove condition"
                    >
                      ×
                    </button>
                  </div>

                  {/* RULE BUILDER */}

                  <div className="condition-builder-row">

                    {/* LEFT */}

                    <div className="rule-group">
                      <span className="rule-label">
                        Indicator
                      </span>

                      <div className="rule-controls">
                        <select
                          value={
                            condition.feature
                          }
                          onChange={(event) =>
                            onUpdateFeature(
                              condition.id,
                              event.target.value
                            )
                          }
                          disabled={isRunning}
                        >
                          {features.map(
                            (feature) => (
                              <option
                                key={
                                  feature.id
                                }
                                value={
                                  feature.id
                                }
                              >
                                {
                                  feature.name
                                }
                              </option>
                            )
                          )}
                        </select>

                        {leftParameter && (
                          <input
                            className="period-input"
                            type="number"
                            min={
                              leftParameter.minimum
                            }
                            max={
                              leftParameter.maximum
                            }
                            step="1"
                            value={
                              condition.period ??
                              ''
                            }
                            onChange={(event) =>
                              updateField(
                                condition.id,
                                'period',
                                event.target
                                  .value === ''
                                  ? ''
                                  : Number(
                                      event
                                        .target
                                        .value
                                    )
                              )
                            }
                            disabled={
                              isRunning
                            }
                          />
                        )}
                      </div>
                    </div>

                    {/* OPERATOR */}

                    <div className="rule-operator">
                      <span className="rule-label">
                        Compare
                      </span>

                      <select
                        value={
                          condition.operator
                        }
                        onChange={(event) =>
                          updateField(
                            condition.id,
                            'operator',
                            event.target.value
                          )
                        }
                        disabled={isRunning}
                      >
                        <option value="<">
                          &lt;
                        </option>

                        <option value="<=">
                          &lt;=
                        </option>

                        <option value=">">
                          &gt;
                        </option>

                        <option value=">=">
                          &gt;=
                        </option>

                        <option value="==">
                          ==
                        </option>

                        <option value="!=">
                          !=
                        </option>
                      </select>
                    </div>

                    {/* RIGHT */}

                    <div className="rule-group right-rule">
                      <span className="rule-label">
                        Against
                      </span>

                      <div className="rule-controls">

                        {/* MULTIPLIER */}

                        <input
                          className="multiplier-input"
                          type="number"
                          min="0"
                          step="0.1"
                          value={
                            multiplier
                          }
                          onChange={(event) =>
                            updateField(
                              condition.id,
                              'rightMultiplier',
                              event.target
                                .value === ''
                                ? ''
                                : Number(
                                    event
                                      .target
                                      .value
                                  )
                            )
                          }
                          disabled={isRunning}
                        />

                        <span className="multiply-symbol">
                          ×
                        </span>

                        {/* TYPE */}

                        <select
                          value={rightType}
                          onChange={(event) =>
                            updateField(
                              condition.id,
                              'rightType',
                              event.target.value
                            )
                          }
                          disabled={isRunning}
                        >
                          <option value="value">
                            Fixed Value
                          </option>

                          <option value="feature">
                            Indicator
                          </option>
                        </select>

                        {/* FIXED VALUE */}

                        {rightType ===
                          'value' && (
                          <input
                            className="value-input"
                            type="number"
                            value={
                              condition.value ??
                              ''
                            }
                            placeholder="Value"
                            onChange={(event) =>
                              updateField(
                                condition.id,
                                'value',
                                event.target.value
                              )
                            }
                            disabled={
                              isRunning
                            }
                          />
                        )}

                        {/* FEATURE */}

                        {rightType ===
                          'feature' && (
                          <>
                            <select
                              value={
                                condition.rightFeature ||
                                ''
                              }
                              onChange={(event) =>
                                updateField(
                                  condition.id,
                                  'rightFeature',
                                  event.target.value
                                )
                              }
                              disabled={
                                isRunning
                              }
                            >
                              <option value="">
                                Select indicator
                              </option>

                              {features.map(
                                (feature) => (
                                  <option
                                    key={
                                      feature.id
                                    }
                                    value={
                                      feature.id
                                    }
                                  >
                                    {
                                      feature.name
                                    }
                                  </option>
                                )
                              )}
                            </select>

                            {rightParameter && (
                              <input
                                className="period-input"
                                type="number"
                                min={
                                  rightParameter.minimum
                                }
                                max={
                                  rightParameter.maximum
                                }
                                step="1"
                                value={
                                  condition.rightPeriod ??
                                  ''
                                }
                                onChange={(event) =>
                                  updateField(
                                    condition.id,
                                    'rightPeriod',
                                    event.target
                                      .value ===
                                      ''
                                      ? ''
                                      : Number(
                                          event
                                            .target
                                            .value
                                        )
                                  )
                                }
                                disabled={
                                  isRunning
                                }
                              />
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* PREVIEW */}

                  <div className="condition-preview">
                    <span className="preview-label">
                      RULE
                    </span>

                    <span className="preview-expression">
                      {leftFeature?.name ||
                        condition.feature}

                      {condition.period
                        ? `(${condition.period})`
                        : ''}

                      <span className="preview-operator">
                        {' '}
                        {condition.operator}{' '}
                      </span>

                      {multiplier !== 1 && (
                        <>
                          <strong>
                            {multiplier}
                          </strong>

                          <span>
                            {' '}×{' '}
                          </span>
                        </>
                      )}

                      {rightType ===
                      'feature'
                        ? (
                          <>
                            <strong>
                              {rightFeature?.name ||
                                'Indicator'}
                            </strong>

                            {condition.rightPeriod && (
                              <>
                                (
                                {
                                  condition.rightPeriod
                                }
                                )
                              </>
                            )}
                          </>
                        )
                        : (
                          condition.value ??
                          'Value'
                        )}
                    </span>
                  </div>
                </div>
              </div>
            )
          }
        )}
    </div>
  )
}

export default ConditionBuilder