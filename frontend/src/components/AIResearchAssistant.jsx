
import { useCallback, useEffect, useRef, useState } from 'react'
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
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : JSON.stringify(data.detail || `Request failed (${response.status})`)
    )
  }

  return data
}

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString()
}

export default function AIResearchAssistant() {
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState('')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [initializing, setInitializing] = useState(true)
  const [error, setError] = useState('')

  const conversationRef = useRef(null)
  const inputRef = useRef(null)

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
      body: JSON.stringify({ title: 'New Research Chat' })
    })

    const session = data.session

    setSessions((current) => [session, ...current])
    setActiveSessionId(session.id)
    setMessages([])

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
    if (element) element.scrollTop = element.scrollHeight
  }, [messages, loading])

  async function handleNewChat() {
    if (loading) return

    setError('')

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
    if (!message || loading) return

    setError('')
    setLoading(true)

    let sessionId = activeSessionId

    try {
      if (!sessionId) {
        sessionId = await createSession()
      }

      setMessages((current) => [
        ...current,
        {
          id: `temp-${Date.now()}`,
          role: 'user',
          content: message
        }
      ])

      setInput('')

      await api(`/ai-research/sessions/${sessionId}/chat`, {
        method: 'POST',
        body: JSON.stringify({ message })
      })

      await loadMessages(sessionId)
      await loadSessions()
    } catch (err) {
      setError(err.message)
      if (sessionId) {
        await loadMessages(sessionId).catch(() => {})
      }
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  function selectSession(sessionId) {
    if (loading) return
    setError('')
    setActiveSessionId(sessionId)
  }

  return (
    <section className="ai-chat-page">
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
            disabled={loading}
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
              disabled={loading}
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
            {error}
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
              <span className="ai-chat-eyebrow">YOUR RESEARCH COMPANION</span>
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
              {messages.map((message) => (
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
                    <div className="ai-chat-message-content">
                      {message.content}
                    </div>
                  </div>
                </article>
              ))}

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
              onChange={(event) => setInput(event.target.value)}
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
              disabled={initializing || loading}
            />

            <div className="ai-chat-composer-bottom">
              <span>Enter to send · Shift + Enter for a new line</span>
              <button
                type="submit"
                disabled={!input.trim() || loading || initializing}
              >
                {loading ? 'Thinking…' : 'Send'}
                <span>↑</span>
              </button>
            </div>
          </form>

          <p className="ai-chat-disclaimer">
            AI responses may be incomplete. Research calculations and
            experiment results must come from the deterministic research engine.
            Live web search is not connected yet.
          </p>
        </div>
      </main>
    </section>
  )
}
