import { useCallback, useEffect, useMemo, useState } from 'react'
import './AIResearchAssistant.css'

const API_BASE_URL = 'http://127.0.0.1:8000'

const DEFAULT_RESEARCH_REQUEST = {
  development_start: '2016-01-01',
  development_end: '2022-12-31',
  validation_start: '2023-01-01',
  validation_end: '2024-12-31',
  holdout_start: '2025-01-01',
  holdout_end: '2025-12-31',
  universe: {
    type: 'all_stocks',
    value: '',
    symbols: [],
    membership_basis: 'point_in_time'
  },
  features: [{ type: 'rsi', parameters: { period: 14 } }],
  entry_conditions: [{
    left: { feature: 'rsi', parameters: { period: 14 } },
    operator: '<',
    right: { value: 30 }
  }],
  evaluation_horizons: [1, 3, 5, 10]
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  })

  const payload = await response.json().catch(() => ({}))

  if (!response.ok) {
    const detail = payload.detail
    throw new Error(
      typeof detail === 'string'
        ? detail
        : JSON.stringify(detail || `Request failed (${response.status})`)
    )
  }

  return payload
}

function pretty(value) {
  return JSON.stringify(value, null, 2)
}

function formatDate(value) {
  if (!value) return ''

  const date = new Date(value)

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString()
}

export default function AIResearchAssistant() {
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState('')
  const [messages, setMessages] = useState([])

  const [researchQuestion, setResearchQuestion] = useState(
    'Does an RSI below 30 improve forward returns compared with a random-entry baseline?'
  )

  const [hypothesis, setHypothesis] = useState(
    'Stocks with RSI(14) below 30 have higher subsequent returns than the random-entry baseline after transaction costs.'
  )

  const [requestJson, setRequestJson] = useState(
    pretty(DEFAULT_RESEARCH_REQUEST)
  )

  const [acknowledgeDevelopmentOnly, setAcknowledgeDevelopmentOnly] =
    useState(false)

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [activeRun, setActiveRun] = useState(null)

  const activeSession = useMemo(
    () => sessions.find((item) => item.id === activeSessionId),
    [sessions, activeSessionId]
  )

  const loadSessions = useCallback(async (preferredId = '') => {
    const data = await api('/ai-research/sessions')
    const rows = data.sessions || []

    setSessions(rows)

    const nextId =
      preferredId ||
      activeSessionId ||
      rows[0]?.id ||
      ''

    if (nextId) {
      setActiveSessionId(nextId)
    }

    return nextId
  }, [activeSessionId])

  const loadMessages = useCallback(async (sessionId) => {
    if (!sessionId) return

    const data = await api(
      `/ai-research/sessions/${sessionId}/messages`
    )

    setMessages(data.messages || [])
  }, [])

  useEffect(() => {
    loadSessions().catch((err) => setError(err.message))
  }, [loadSessions])

  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId).catch(
        (err) => setError(err.message)
      )
    } else {
      setMessages([])
    }
  }, [activeSessionId, loadMessages])

  useEffect(() => {
    if (
      !activeRun?.runId ||
      !activeSessionId ||
      ['completed', 'failed', 'cancelled'].includes(activeRun.status)
    ) {
      return undefined
    }

    let cancelled = false

    const poll = async () => {
      try {
        const data = await api(
          `/ai-research/sessions/${activeSessionId}/runs/${activeRun.runId}`
        )

        if (cancelled) return

        const run = data.run

        setActiveRun((current) =>
          current?.runId === run.id
            ? {
                ...current,
                status: run.status,
                step: run.current_step,
                output: run.output_data,
                error: run.error_message
              }
            : current
        )

        if (
          ['completed', 'failed', 'cancelled'].includes(run.status)
        ) {
          await loadMessages(activeSessionId)
          await loadSessions(activeSessionId)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message)
        }
      }
    }

    poll()

    const timer = window.setInterval(poll, 2500)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [
    activeRun?.runId,
    activeRun?.status,
    activeSessionId,
    loadMessages,
    loadSessions
  ])

  async function createSession() {
    setBusy(true)
    setError('')
    setNotice('')

    try {
      const data = await api('/ai-research/sessions', {
        method: 'POST',
        body: JSON.stringify({
          title: 'New Research Chat'
        })
      })

      await loadSessions(data.session.id)

      setMessages([])
      setActiveRun(null)

      setNotice('New research session created.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function submitProposal(event) {
    event.preventDefault()

    setBusy(true)
    setError('')
    setNotice('')

    try {
      if (!activeSessionId) {
        throw new Error(
          'Create or select a research session first.'
        )
      }

      const baseResearchRequest = JSON.parse(requestJson)

      const data = await api(
        `/ai-research/sessions/${activeSessionId}/propose`,
        {
          method: 'POST',
          body: JSON.stringify({
            research_question: researchQuestion.trim(),
            hypothesis: hypothesis.trim(),
            base_research_request: baseResearchRequest
          })
        }
      )

      setActiveRun({
        runId: data.agent_run_id,
        ledgerId: data.ledger_id,
        status: data.status
      })

      await loadMessages(activeSessionId)

      setNotice(
        `Proposal generated with ${data.model || 'the configured model'}. Review it below before approving.`
      )
    } catch (err) {
      setError(
        err instanceof SyntaxError
          ? 'Research request must be valid JSON.'
          : err.message
      )
    } finally {
      setBusy(false)
    }
  }

  async function decideProposal(ledgerId, approve) {
    setBusy(true)
    setError('')
    setNotice('')

    try {
      const path =
        `/ai-research/sessions/${activeSessionId}` +
        `/ledger/${ledgerId}/` +
        `${approve ? 'approve' : 'reject'}`

      const body = approve
        ? {
            acknowledge_development_only:
              acknowledgeDevelopmentOnly
          }
        : {
            reason: 'Rejected by user'
          }

      const data = await api(path, {
        method: 'POST',
        body: JSON.stringify(body)
      })

      setNotice(
        approve
          ? 'Approved. Research execution has been queued.'
          : 'Proposal rejected.'
      )

      if (approve) {
        setActiveRun((current) =>
          current
            ? {
                ...current,
                status: data.execution_status || 'queued'
              }
            : current
        )
      }

      await loadMessages(activeSessionId)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="ai-research-page">
      <header className="ai-research-header">
        <div>
          <div className="ai-eyebrow">
            STOCK SCANNER / RESEARCH WORKSPACE
          </div>

          <h1>AI Research Assistant</h1>

          <p>
            Explore a hypothesis, review a proposed experiment,
            then explicitly approve execution.
          </p>
        </div>

        <button
          className="ai-primary-button"
          onClick={createSession}
          disabled={busy}
        >
          + New session
        </button>
      </header>

      {error && (
        <div className="ai-alert ai-alert-error">
          {error}
        </div>
      )}

      {notice && (
        <div className="ai-alert ai-alert-success">
          {notice}
        </div>
      )}

      <div className="ai-research-layout">
        <aside className="ai-session-panel">
          <div className="ai-panel-heading">
            Research sessions
          </div>

          {sessions.length === 0 && (
            <p className="ai-muted">
              No sessions yet. Create one to begin.
            </p>
          )}

          {sessions.map((session) => (
            <button
              key={session.id}
              className={
                `ai-session-item ${
                  session.id === activeSessionId ? 'selected' : ''
                }`
              }
              onClick={() => {
                setActiveSessionId(session.id)
                setActiveRun(null)
                setError('')
              }}
            >
              <strong>
                {session.title || 'Research chat'}
              </strong>

              <span>
                {formatDate(
                  session.updated_at || session.created_at
                )}
              </span>
            </button>
          ))}
        </aside>

        <div className="ai-main-panel">
          <div className="ai-panel-heading">
            {activeSession?.title || 'New research session'}
          </div>

          <div className="ai-conversation">
            {messages.length === 0 && (
              <div className="ai-empty-state">
                <div className="ai-empty-icon">⌁</div>

                <h2>Start with a research question</h2>

                <p>
                  Describe what you want to investigate.
                  The assistant will propose a test; it will
                  not execute anything until you approve it.
                </p>
              </div>
            )}

            {messages.map((message) => (
              <article
                key={message.id}
                className={`ai-message ai-message-${message.role}`}
              >
                <div className="ai-message-role">
                  {message.role === 'user'
                    ? 'YOU'
                    : 'RESEARCH ASSISTANT'}
                </div>

                <div className="ai-message-content">
                  {message.content}
                </div>

                {message.metadata?.proposal && (
                  <div className="ai-proposal-card">
                    <div className="ai-proposal-topline">
                      <strong>Experiment proposal</strong>

                      <span>
                        {message.metadata.proposal.experiment_type ||
                          'Research experiment'}
                      </span>
                    </div>

                    <h3>
                      {message.metadata.proposal.research_question}
                    </h3>

                    <p>
                      <b>Hypothesis:</b>{' '}
                      {message.metadata.proposal.hypothesis}
                    </p>

                    <p>
                      <b>Rationale:</b>{' '}
                      {message.metadata.proposal.rationale}
                    </p>

                    <p>
                      <b>Expected learning:</b>{' '}
                      {message.metadata.proposal.expected_learning}
                    </p>

                    <div className="ai-proposal-actions">
                      <label className="ai-check-label">
                        <input
                          type="checkbox"
                          checked={acknowledgeDevelopmentOnly}
                          onChange={(event) =>
                            setAcknowledgeDevelopmentOnly(
                              event.target.checked
                            )
                          }
                        />

                        I understand this proposal may run
                        without complete validation/holdout stages.
                      </label>

                      <div className="ai-action-row">
                        <button
                          className="ai-secondary-button"
                          disabled={busy}
                          onClick={() =>
                            decideProposal(
                              message.metadata.ledger_id,
                              false
                            )
                          }
                        >
                          Reject
                        </button>

                        <button
                          className="ai-primary-button"
                          disabled={busy}
                          onClick={() =>
                            decideProposal(
                              message.metadata.ledger_id,
                              true
                            )
                          }
                        >
                          Approve &amp; execute
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </article>
            ))}
          </div>

          {activeRun && (
            <div className="ai-run-status">
              <div>
                <strong>Execution status</strong>

                <span
                  className={
                    `ai-status-pill status-${activeRun.status}`
                  }
                >
                  {activeRun.status}
                </span>
              </div>

              <p>
                {activeRun.step || 'Waiting for status update'}

                {activeRun.error
                  ? ` — ${activeRun.error}`
                  : ''}
              </p>

              {activeRun.output?.experiment_id && (
                <p>
                  Saved experiment:{' '}
                  <b>{activeRun.output.experiment_id}</b>
                </p>
              )}
            </div>
          )}

          <form
            className="ai-composer"
            onSubmit={submitProposal}
          >
            <div className="ai-panel-heading">
              Propose a new experiment
            </div>

            <label>Research question</label>

            <textarea
              value={researchQuestion}
              onChange={(event) =>
                setResearchQuestion(event.target.value)
              }
              rows={2}
              minLength={5}
              maxLength={1000}
              required
            />

            <label>Hypothesis</label>

            <textarea
              value={hypothesis}
              onChange={(event) =>
                setHypothesis(event.target.value)
              }
              rows={2}
              minLength={5}
              maxLength={1000}
              required
            />

            <details className="ai-config-details">
              <summary>
                Research configuration (JSON)
              </summary>

              <p>
                Configure dates, universe, features,
                conditions and evaluation horizons.
                The API validates this against the research schema.
              </p>

              <textarea
                className="ai-json-editor"
                value={requestJson}
                onChange={(event) =>
                  setRequestJson(event.target.value)
                }
                spellCheck="false"
                rows={18}
              />
            </details>

            <div className="ai-composer-footer">
              <span>
                Python engine owns calculations.
                AI only proposes and interprets.
              </span>

              <button
                className="ai-primary-button"
                type="submit"
                disabled={busy || !activeSessionId}
              >
                {busy ? 'Working…' : 'Generate proposal'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </section>
  )
}