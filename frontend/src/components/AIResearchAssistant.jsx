
import { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './AIResearchAssistant.css'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const detail = data.detail
    const message =
      typeof detail === 'string'
        ? detail
        : detail?.message ||
          JSON.stringify(detail || `Request failed (${response.status})`)

    const error = new Error(message)
    error.code = detail?.code || 'REQUEST_FAILED'
    error.status = response.status
    throw error
  }

  return data
}

function formatDate(value) {
  if (!value) return ''

  const date = new Date(value)

  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleDateString()
}

function MarkdownMessage({ content }) {
  return (
    <div className="ai-chat-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ ...props }) => (
            <a {...props} target="_blank" rel="noreferrer" />
          ),
          code: ({ className, children, ...props }) => {
            const isBlock = Boolean(className)

            return isBlock ? (
              <code className={className} {...props}>
                {children}
              </code>
            ) : (
              <code className="ai-inline-code" {...props}>
                {children}
              </code>
            )
          },
          pre: ({ children }) => (
            <pre className="ai-code-block">{children}</pre>
          ),
          table: ({ children }) => (
            <div className="ai-table-wrap">
              <table>{children}</table>
            </div>
          )
        }}
      >
        {content || ''}
      </ReactMarkdown>
    </div>
  )
}

function ProposalCard({
  message,
  busy,
  onApprove,
  onReject,
  onRefresh
}) {
  const metadata = message.metadata || {}
  const ledgerId = metadata.ledger_id
  const runId = metadata.agent_run_id
  const workflowStatus = metadata.workflow_status

  const [acknowledgeDevelopmentOnly, setAcknowledgeDevelopmentOnly] =
    useState(false)

  const [requiresDevelopmentAcknowledgement, setRequiresDevelopmentAcknowledgement] =
    useState(false)

  const [actionError, setActionError] = useState('')
  const [actionStatus, setActionStatus] = useState('')

  if (workflowStatus !== 'proposal_saved' || !ledgerId || !runId) {
    return <MarkdownMessage content={message.content} />
  }

  async function handleApprove() {
    setActionError('')
    setActionStatus('')

    try {
      await onApprove({
        ledgerId,
        acknowledgeDevelopmentOnly
      })

      setActionStatus('Approval submitted. Research has been queued.')
      setRequiresDevelopmentAcknowledgement(false)
    } catch (error) {
      if (
        error.status === 400 &&
        error.message.toLowerCase().includes('development-only')
      ) {
        setRequiresDevelopmentAcknowledgement(true)
        setActionError(
          'This proposal does not include complete validation and holdout stages. Review the limitation and explicitly acknowledge it before proceeding.'
        )
        return
      }

      setActionError(error.message)
    }
  }

  async function handleReject() {
    setActionError('')
    setActionStatus('')

    try {
      await onReject({ ledgerId })
      setActionStatus('Proposal rejected.')
    } catch (error) {
      setActionError(error.message)
    }
  }

  return (
    <div className="ai-proposal-card">
      <div className="ai-proposal-card-header">
        <div>
          <span className="ai-proposal-eyebrow">RESEARCH PROPOSAL</span>
          <h3>Experiment awaiting your decision</h3>
        </div>

        <span className="ai-proposal-status">PENDING APPROVAL</span>
      </div>

      <div className="ai-proposal-content">
        <MarkdownMessage content={message.content} />
      </div>

      <div className="ai-proposal-identifiers">
        <div>
          <span>Ledger ID</span>
          <code>{ledgerId}</code>
        </div>
        <div>
          <span>Agent run ID</span>
          <code>{runId}</code>
        </div>
      </div>

      {actionError && (
        <div className="ai-proposal-error" role="alert">
          {actionError}
        </div>
      )}

      {requiresDevelopmentAcknowledgement && (
        <label className="ai-proposal-acknowledgement">
          <input
            type="checkbox"
            checked={acknowledgeDevelopmentOnly}
            onChange={(event) =>
              setAcknowledgeDevelopmentOnly(event.target.checked)
            }
          />
          <span>
            I understand this is a development-only run and does not
            provide complete validation or final holdout evidence.
          </span>
        </label>
      )}

      {actionStatus && (
        <div className="ai-proposal-success" role="status">
          {actionStatus}
        </div>
      )}

      <div className="ai-proposal-actions">
        <button
          type="button"
          className="ai-proposal-approve"
          onClick={handleApprove}
          disabled={
            busy ||
            (requiresDevelopmentAcknowledgement &&
              !acknowledgeDevelopmentOnly) ||
            Boolean(actionStatus)
          }
        >
          {busy ? 'Processing…' : 'Approve proposal'}
        </button>

        <button
          type="button"
          className="ai-proposal-reject"
          onClick={handleReject}
          disabled={busy || Boolean(actionStatus)}
        >
          Reject
        </button>

        <button
          type="button"
          className="ai-proposal-refresh"
          onClick={() => onRefresh(runId)}
          disabled={busy}
        >
          Refresh status
        </button>
      </div>

      <p className="ai-proposal-disclaimer">
        Approval queues the existing deterministic research pipeline.
        The proposal itself has not been executed.
      </p>
    </div>
  )
}

export default function AIResearchAssistant() {
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState('')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [actionBusy, setActionBusy] = useState(false)
  const [initializing, setInitializing] = useState(true)
  const [error, setError] = useState('')
  const [runStatuses, setRunStatuses] = useState({})

  const conversationRef = useRef(null)
  const inputRef = useRef(null)
  const pendingMessageIdRef = useRef(null)

  const loadMessages = useCallback(async (sessionId) => {
    if (!sessionId) return

    const data = await api(
      `/ai-research/sessions/${sessionId}/messages`
    )

    setMessages(data.messages || [])
  }, [])

  const loadSessions = useCallback(async () => {
    const data = await api('/ai-research/sessions')
    const rows = data.sessions || []

    setSessions(rows)
    return rows
  }, [])

  const createSession = useCallback(async () => {
    const data = await api('/ai-research/sessions', {
      method: 'POST',
      body: JSON.stringify({
        title: 'New Research Chat'
      })
    })

    const session = data.session

    setSessions((current) => [
      session,
      ...current.filter((item) => item.id !== session.id)
    ])

    setActiveSessionId(session.id)
    setMessages([])
    setRunStatuses({})

    return session.id
  }, [])

  useEffect(() => {
    let cancelled = false

    async function initialize() {
      try {
        const rows = await loadSessions()

        if (cancelled) return

        if (rows.length > 0) {
          setActiveSessionId(rows[0].id)
        } else {
          await createSession()
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setInitializing(false)
      }
    }

    initialize()

    return () => {
      cancelled = true
    }
  }, [loadSessions, createSession])

  useEffect(() => {
    if (!activeSessionId) return

    loadMessages(activeSessionId).catch((err) => {
      setError(err.message)
    })
  }, [activeSessionId, loadMessages])

  useEffect(() => {
    const element = conversationRef.current

    if (element) {
      element.scrollTop = element.scrollHeight
    }
  }, [messages, loading])

  async function handleNewChat() {
    if (loading || actionBusy) return

    setError('')
    pendingMessageIdRef.current = null
    setInput('')

    try {
      await createSession()
      inputRef.current?.focus()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleSend(event) {
    event.preventDefault()

    const message = input.trim()

    if (!message || loading || initializing || actionBusy) return

    setError('')
    setLoading(true)

    let sessionId = activeSessionId

    const clientMessageId =
      pendingMessageIdRef.current ||
      (globalThis.crypto?.randomUUID
        ? globalThis.crypto.randomUUID()
        : `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`)

    pendingMessageIdRef.current = clientMessageId

    try {
      if (!sessionId) {
        sessionId = await createSession()
      }

      const alreadyDisplayed = messages.some(
        (item) =>
          item.role === 'user' &&
          item.metadata?.client_message_id === clientMessageId
      )

      if (!alreadyDisplayed) {
        setMessages((current) => [
          ...current,
          {
            id: `temp-${clientMessageId}`,
            role: 'user',
            content: message,
            metadata: {
              client_message_id: clientMessageId
            }
          }
        ])
      }

      setInput('')

      await api(
        `/ai-research/sessions/${sessionId}/chat`,
        {
          method: 'POST',
          body: JSON.stringify({
            message,
            client_message_id: clientMessageId
          })
        }
      )

      pendingMessageIdRef.current = null

      await loadMessages(sessionId)
      await loadSessions()
    } catch (err) {
      setError(err.message)
      setInput(message)

      if (sessionId) {
        await loadMessages(sessionId).catch(() => {})
      }
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  async function handleApprove({
    ledgerId,
    acknowledgeDevelopmentOnly
  }) {
    if (!activeSessionId) return

    setActionBusy(true)

    try {
      const result = await api(
        `/ai-research/sessions/${activeSessionId}/ledger/${ledgerId}/approve`,
        {
          method: 'POST',
          body: JSON.stringify({
            acknowledge_development_only:
              acknowledgeDevelopmentOnly
          })
        }
      )

      setRunStatuses((current) => ({
        ...current,
        [result.agent_run_id]: 'pending'
      }))

      await refreshRunStatus(result.agent_run_id)
      await loadMessages(activeSessionId)
    } finally {
      setActionBusy(false)
    }
  }

  async function handleReject({ ledgerId }) {
    if (!activeSessionId) return

    const confirmed = window.confirm(
      'Reject this research proposal? It will not be executed.'
    )

    if (!confirmed) return

    setActionBusy(true)

    try {
      await api(
        `/ai-research/sessions/${activeSessionId}/ledger/${ledgerId}/reject`,
        {
          method: 'POST',
          body: JSON.stringify({
            reason: 'Rejected by user'
          })
        }
      )

      await loadMessages(activeSessionId)
    } finally {
      setActionBusy(false)
    }
  }

  async function refreshRunStatus(runId) {
    if (!activeSessionId || !runId) return

    try {
      const result = await api(
        `/ai-research/sessions/${activeSessionId}/runs/${runId}`
      )

      const run = result.run

      setRunStatuses((current) => ({
        ...current,
        [runId]: run.status
      }))

      return run.status
    } catch (err) {
      setError(`Could not refresh research status: ${err.message}`)
      return null
    }
  }

  function selectSession(sessionId) {
    if (loading || actionBusy) return

    setError('')
    setInput('')
    pendingMessageIdRef.current = null
    setRunStatuses({})
    setActiveSessionId(sessionId)
  }

  return (
    <section className="ai-chat-page">
      <style>{`
        .ai-proposal-card {
          margin-top: 16px;
          padding: 17px;
          border: 1px solid #24536a;
          border-radius: 10px;
          background: #091b29;
        }
        .ai-proposal-card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          flex-wrap: wrap;
          gap: 12px;
          padding-bottom: 13px;
          border-bottom: 1px solid #1c394c;
        }
        .ai-proposal-eyebrow {
          color: #48cde8;
          font-size: 9px;
          font-weight: 800;
          letter-spacing: 1.3px;
        }
        .ai-proposal-card h3 {
          margin: 6px 0 0;
          color: #e3f2fa;
          font-size: 15px;
        }
        .ai-proposal-status {
          padding: 5px 8px;
          border: 1px solid #80652e;
          border-radius: 5px;
          color: #f0ce83;
          font-size: 9px;
          font-weight: 800;
        }
        .ai-proposal-content {
          padding: 15px 0 5px;
        }
        .ai-proposal-identifiers {
          display: grid;
          gap: 8px;
          padding: 12px;
          border: 1px solid #1c3548;
          border-radius: 7px;
          background: #071521;
        }
        .ai-proposal-identifiers div {
          display: grid;
          gap: 4px;
          min-width: 0;
        }
        .ai-proposal-identifiers span {
          color: #718da1;
          font-size: 9px;
        }
        .ai-proposal-identifiers code {
          color: #9bdced;
          font-size: 10px;
          overflow-wrap: anywhere;
        }
        .ai-proposal-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 14px;
        }
        .ai-proposal-actions button {
          padding: 9px 12px;
          border: 1px solid #31536a;
          border-radius: 6px;
          background: #10283a;
          color: #c9e1ed;
          font-size: 10px;
          font-weight: 700;
          cursor: pointer;
        }
        .ai-proposal-actions button:disabled {
          opacity: .45;
          cursor: not-allowed;
        }
        .ai-proposal-actions .ai-proposal-approve {
          border-color: #187b70;
          background: #0d3b38;
          color: #9ce8d4;
        }
        .ai-proposal-actions .ai-proposal-reject {
          border-color: #75434a;
          background: #321e25;
          color: #f0b2b6;
        }
        .ai-proposal-acknowledgement {
          display: flex;
          align-items: flex-start;
          gap: 9px;
          margin-top: 13px;
          padding: 11px;
          border: 1px solid #80652e;
          border-radius: 7px;
          color: #e8d5a5;
          font-size: 11px;
          line-height: 1.6;
        }
        .ai-proposal-acknowledgement input {
          margin-top: 3px;
        }
        .ai-proposal-error,
        .ai-proposal-success {
          margin-top: 12px;
          padding: 10px;
          border-radius: 6px;
          font-size: 11px;
          line-height: 1.6;
        }
        .ai-proposal-error {
          border: 1px solid #75434a;
          background: #291920;
          color: #f0b2b6;
        }
        .ai-proposal-success {
          border: 1px solid #246b5d;
          background: #102a29;
          color: #9ce8d4;
        }
        .ai-proposal-disclaimer {
          margin: 12px 0 0;
          color: #71899a;
          font-size: 9px;
          line-height: 1.5;
        }
      `}</style>

      <aside className="ai-chat-sidebar">
        <div className="ai-chat-sidebar-top">
          <div className="ai-chat-brand">
            <span className="ai-chat-brand-icon">⌁</span>
            <div>
              <strong>Research AI</strong>
              <small>Stock Scanner</small>
            </div>
          </div>

          <button
            className="ai-new-chat-button"
            onClick={handleNewChat}
            disabled={loading || actionBusy}
          >
            + New chat
          </button>
        </div>

        <div className="ai-chat-history-label">
          RECENT CONVERSATIONS
        </div>

        <div className="ai-chat-session-list">
          {sessions.map((session) => (
            <button
              key={session.id}
              className={`ai-chat-session ${
                session.id === activeSessionId ? 'active' : ''
              }`}
              onClick={() => selectSession(session.id)}
              disabled={loading || actionBusy}
            >
              <span className="ai-chat-session-title">
                {session.title || 'Research conversation'}
              </span>

              <small>
                {formatDate(session.updated_at || session.created_at)}
              </small>
            </button>
          ))}

          {sessions.length === 0 && !initializing && (
            <p className="ai-chat-empty-history">
              Your conversations will appear here.
            </p>
          )}
        </div>

        <div className="ai-chat-sidebar-footer">
          <span className="ai-online-dot" />
          Research assistant
          <small>Conversational mode</small>
        </div>
      </aside>

      <main className="ai-chat-main">
        <header className="ai-chat-header">
          <div>
            <span className="ai-chat-eyebrow">
              STOCK RESEARCH WORKSPACE
            </span>

            <h1>AI Research Assistant</h1>

            <p>
              Ask questions, explore hypotheses and understand your research.
            </p>
          </div>

          <span className="ai-chat-version">BETA</span>
        </header>

        {error && (
          <div className="ai-chat-error">
            <span>{error}</span>
            <button onClick={() => setError('')}>Dismiss</button>
          </div>
        )}

        <div className="ai-chat-conversation" ref={conversationRef}>
          {initializing ? (
            <div className="ai-chat-welcome">
              <div className="ai-chat-welcome-icon">⌁</div>
              <h2>Preparing your research workspace</h2>
            </div>
          ) : messages.length === 0 ? (
            <div className="ai-chat-welcome">
              <div className="ai-chat-welcome-icon">⌁</div>

              <span className="ai-chat-eyebrow">
                YOUR RESEARCH COMPANION
              </span>

              <h2>What would you like to investigate?</h2>

              <p>
                Ask about market concepts, statistics, existing experiments
                or a research hypothesis. I’ll help clarify the question
                before suggesting a research workflow.
              </p>

              <div className="ai-chat-suggestions">
                {[
                  'Explain how RSI works and its limitations.',
                  'Does delivery volume improve returns after an oversold signal?',
                  'How should I avoid look-ahead bias in a backtest?'
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                  >
                    {suggestion}
                    <span>↗</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="ai-chat-message-list">
              {messages.map((message) => {
                const metadata = message.metadata || {}
                const runStatus = metadata.agent_run_id
                  ? runStatuses[metadata.agent_run_id]
                  : null

                return (
                  <article
                    key={message.id}
                    className={`ai-chat-message ${
                      message.role === 'user' ? 'user' : 'assistant'
                    }`}
                  >
                    <div className="ai-chat-avatar">
                      {message.role === 'user' ? 'YOU' : 'AI'}
                    </div>

                    <div className="ai-chat-message-body">
                      <div className="ai-chat-message-label">
                        {message.role === 'user'
                          ? 'You'
                          : 'Research Assistant'}
                      </div>

                      {message.role === 'user' ? (
                        <div className="ai-chat-message-content">
                          {message.content}
                        </div>
                      ) : (
                        <>
                          <ProposalCard
                            message={message}
                            busy={actionBusy}
                            onApprove={handleApprove}
                            onReject={handleReject}
                            onRefresh={refreshRunStatus}
                          />

                          {runStatus && (
                            <div className="ai-proposal-success">
                              Current execution status: <strong>{runStatus}</strong>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </article>
                )
              })}

              {loading && (
                <div className="ai-chat-thinking">
                  <span />
                  <span />
                  <span />
                  <small>Thinking through your question</small>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="ai-chat-composer-area">
          <form className="ai-chat-composer" onSubmit={handleSend}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(event) => {
                const nextValue = event.target.value

                if (nextValue.trim() !== input.trim()) {
                  pendingMessageIdRef.current = null
                }

                setInput(nextValue)
              }}
              onKeyDown={(event) => {
                if (
                  event.key === 'Enter' &&
                  !event.shiftKey &&
                  !event.nativeEvent.isComposing
                ) {
                  event.preventDefault()
                  event.currentTarget.form.requestSubmit()
                }
              }}
              placeholder="Ask a research question..."
              rows={2}
              maxLength={4000}
              disabled={initializing || loading || actionBusy}
            />

            <div className="ai-chat-composer-bottom">
              <span>Enter to send · Shift + Enter for a new line</span>

              <button
                type="submit"
                disabled={
                  !input.trim() ||
                  loading ||
                  initializing ||
                  actionBusy
                }
              >
                {loading ? 'Thinking…' : 'Send'}
                <span>↑</span>
              </button>
            </div>
          </form>

          <p className="ai-chat-disclaimer">
            Research calculations and experiment results must come from
            the deterministic Python engine. Live web search is not
            connected yet.
          </p>
        </div>
      </main>
    </section>
  )
}
