import { type FormEvent, useEffect, useRef, useState } from 'react'
import './App.css'

type Tab = 'evidence' | 'assertions' | 'world'

type Health = {
  status: string
  service: string
  model: {
    status: string
    error: string | null
  }
  dense_recovery: {
    status: string
  }
}

type Evidence = {
  id: number
  session_id: string
  role: string
  content: string
  created_at: string
}

type Session = {
  session_id: string
  message_count: number
  first_message_id: number
  last_message_id: number
  created_at: string
  updated_at: string
}

type ChatMessage = {
  id: number
  session_id: string
  role: string
  content: string
  created_at: string
}

type SessionDetail = {
  session_id: string
  message_count: number
  returned_count: number
  has_more: boolean
  messages: ChatMessage[]
}

type ChatResponse = {
  reply: string | null
  status: {
    overall: string
  }
  error: string | null
}


const WELCOME_PROMPTS = [
  "What's on your mind?",
  "How are you doing today?",
  "What are you thinking about?",
  "What should we work on?",
  "Anything you want to talk about?",
  "Where should we pick up?",
  "What would you like to explore?",
  "How can I help today?",
]

function pickWelcomePrompt(current?: string) {
  const candidates = current
    ? WELCOME_PROMPTS.filter((prompt) => prompt !== current)
    : WELCOME_PROMPTS

  return candidates[
    Math.floor(Math.random() * candidates.length)
  ] ?? WELCOME_PROMPTS[0]
}


function App() {
  const [inspectOpen, setInspectOpen] = useState(false)
  const [conversationOpen, setConversationOpen] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const hour = new Date().getHours()
    return hour >= 7 && hour < 19 ? 'light' : 'dark'
  })
  const [tab, setTab] = useState<Tab>('evidence')
  const [evidence, setEvidence] = useState<Evidence[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [healthError, setHealthError] = useState(false)
  const [sessions, setSessions] = useState<Session[]>([])
  const [selectedSession, setSelectedSession] = useState('')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const composerRef = useRef<HTMLTextAreaElement | null>(null)
  const [composerExpanded, setComposerExpanded] = useState(false)
  const [sending, setSending] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const [welcomePrompt, setWelcomePrompt] = useState(
    () => pickWelcomePrompt(),
  )



  useEffect(() => {
    async function loadHealth() {
      try {
        const response = await fetch('/api/health')
        if (!response.ok) throw new Error()

        const data: Health = await response.json()
        setHealth(data)
        setHealthError(false)
      } catch {
        setHealth(null)
        setHealthError(true)
      }
    }

    loadHealth()
    const timer = window.setInterval(loadHealth, 10000)

    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    async function loadSessions() {
      try {
        const response = await fetch('/api/sessions')
        if (!response.ok) return

        const data: Session[] = await response.json()
        setSessions(data)
      } catch {
        setSessions([])
      }
    }

    loadSessions()
  }, [])


  function isCompactLayout() {
    return window.matchMedia('(max-width: 900px)').matches
  }

  async function selectSession(sessionId: string) {
    setDraft('')
    setChatError(null)
    setSelectedSession(sessionId)

    if (!sessionId) {
      setChatMessages([])
      return
    }

    try {
      const response = await fetch(
        `/api/sessions/${encodeURIComponent(sessionId)}`,
      )

      if (!response.ok) {
        setChatMessages([])
        return
      }

      const data: SessionDetail = await response.json()
      setChatMessages(data.messages)
    } catch {
      setChatMessages([])
    }
  }

  useEffect(() => {
    const textarea = composerRef.current
    if (!textarea) return

    textarea.style.height = 'auto'

    const scrollHeight = textarea.scrollHeight
    const nextHeight = Math.min(scrollHeight, 180)

    textarea.style.height = `${nextHeight}px`
    textarea.style.overflowY =
      scrollHeight > 180 ? 'auto' : 'hidden'

    setComposerExpanded(scrollHeight > 44)
  }, [draft])

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const message = draft.trim()
    if (!message || sending) return

    const wasNew = !selectedSession
    const sessionId = selectedSession || `chat-${Date.now()}`
    const previousMessages = chatMessages

    const optimisticMessage: ChatMessage = {
      id: -Date.now(),
      session_id: sessionId,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    }

    /*
     * Optimistic UI:
     * acknowledge the user's send immediately while SQLite remains
     * the canonical source once the backend turn completes.
     */
    setDraft('')
    setChatMessages([
      ...previousMessages,
      optimisticMessage,
    ])
    setSending(true)
    setChatError(null)

    if (wasNew) {
      setSelectedSession(sessionId)
    }

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          message,
        }),
      })

      const data: ChatResponse = await response.json()

      if (
        !response.ok ||
        !data.reply ||
        data.status?.overall === 'FAILED'
      ) {
        throw new Error(
          data.error || 'Corvus could not complete the turn.',
        )
      }

      /*
       * Replace the temporary optimistic message with canonical
       * SQLite-backed session history.
       */
      await selectSession(sessionId)

      const sessionsResponse = await fetch('/api/sessions')
      if (sessionsResponse.ok) {
        const sessionData: Session[] =
          await sessionsResponse.json()
        setSessions(sessionData)
      }
    } catch (error) {
      /*
       * Corvus commits user evidence before model generation.
       * If the backend received the message but generation failed,
       * preserve whatever SQLite actually contains.
       */
      let canonicalRecovered = false

      try {
        const historyResponse = await fetch(
          `/api/sessions/${encodeURIComponent(sessionId)}`,
        )

        if (historyResponse.ok) {
          const history: SessionDetail =
            await historyResponse.json()

          setSelectedSession(sessionId)
          setChatMessages(history.messages)
          canonicalRecovered = true
        }
      } catch {
        // Fall through to local rollback below.
      }

      /*
       * If no canonical session exists, the send likely never reached
       * Corvus. Restore the draft so the user can retry safely.
       */
      if (!canonicalRecovered) {
        setChatMessages(previousMessages)
        setDraft(message)

        if (wasNew) {
          setSelectedSession('')
        }
      }

      setChatError(
        error instanceof Error
          ? error.message
          : 'Unable to reach Corvus.',
      )
    } finally {
      setSending(false)
    }
  }

  async function openInspector() {
    const response = await fetch('/api/evidence')
    const data = await response.json()
    setEvidence(data)
    if (isCompactLayout()) setConversationOpen(false)
    setInspectOpen(true)
  }

  return (
    <main className="corvus-app" data-theme={theme}>
      <header className="topbar">
        <div className="topbar-brand">
          <button
            type="button"
            className="ghost-button sidebar-toggle"
            aria-label="Open conversations"
            onClick={() => {
              if (isCompactLayout()) setInspectOpen(false)
              setConversationOpen(!conversationOpen)
            }}
          >
            ☰
          </button>

          <div>
            <span className="eyebrow">CORVUS</span>
            <h1>Memory Playground</h1>
          </div>
        </div>

        <div className="topbar-actions">
          <span
            className={`status ${
              healthError
                ? 'health-offline'
                : !health
                  ? 'health-checking'
                  : health.status === 'OK'
                    ? 'health-healthy'
                    : 'health-degraded'
            }`}
            title={
              healthError
                ? 'Local · Offline'
                : !health
                  ? 'Local · Checking'
                  : `Local · ${
                      health.status === 'OK' ? 'Healthy' : 'Degraded'
                    } · Model ${health.model.status} · Retrieval ${
                      health.dense_recovery.status
                    }`
            }
          >
            <span className="status-dot" aria-hidden="true" />
            <span>Local</span>
          </span>

          <button
            type="button"
            className="ghost-button"
            onClick={() =>
              setTheme(theme === 'dark' ? 'light' : 'dark')
            }
          >
            {theme === 'dark' ? '☀' : '☾'}
          </button>

          <button
            type="button"
            className="ghost-button"
            onClick={() => {
              if (inspectOpen) {
                setInspectOpen(false)
              } else {
                openInspector()
              }
            }}
          >
            Inspect
          </button>
        </div>
      </header>

      {conversationOpen && (
        <button
          type="button"
          className="drawer-backdrop"
          aria-label="Close conversations"
          onClick={() => setConversationOpen(false)}
        />
      )}

      <div
        className={`workspace ${
          conversationOpen ? 'conversation-open' : ''
        } ${inspectOpen ? 'inspector-open' : ''}`}
      >
        <aside
          className={`conversation-sidebar ${conversationOpen ? 'open' : ''}`}
        >
          <div className="conversation-sidebar-header">
            <span>Conversations</span>
            <button
              type="button"
              className="close-button"
              aria-label="Close conversations"
              onClick={() => setConversationOpen(false)}
            >
              ×
            </button>
          </div>

          <button
            type="button"
            className="new-chat-button"
            onClick={() => {
              setWelcomePrompt((current) => pickWelcomePrompt(current))
              selectSession('')
              if (isCompactLayout()) setConversationOpen(false)
            }}
          >
            + New chat
          </button>

          <div className="conversation-list">
            {sessions.map((session) => (
              <button
                type="button"
                key={session.session_id}
                className={
                  selectedSession === session.session_id
                    ? 'conversation-item active'
                    : 'conversation-item'
                }
                onClick={() => {
                  selectSession(session.session_id)
                  if (isCompactLayout()) setConversationOpen(false)
                }}
              >
                <span>{session.session_id}</span>
                <small>{session.message_count} messages</small>
              </button>
            ))}
          </div>
        </aside>

        <section className="chat-panel">
          <div className="messages">
          {chatMessages.length === 0 && !sending ? (
            <div className="welcome">
              <h2>Corvus</h2>
              <p>{welcomePrompt}</p>
            </div>
          ) : (
            <div className="chat-history">
              {chatMessages.map((message) => (
                <article
                  className={`chat-message ${message.role}`}
                  key={message.id}
                >
                  <div className="message-body">
                    <p>{message.content}</p>
                  </div>
                </article>
              ))}

              {sending && (
                <article className="chat-message assistant thinking-message">
                  <div className="message-body">
                    <div
                      className="thinking-indicator"
                      aria-label="Corvus is thinking"
                    >
                      <span>Thinking</span>
                      <i />
                    </div>
                  </div>
                </article>
              )}
            </div>
          )}
        </div>

        <form
          className={`composer ${
            chatMessages.length === 0
              ? 'composer-new'
              : 'composer-established'
          } ${
            composerExpanded
              ? 'composer-expanded'
              : 'composer-single'
          }`}
          onSubmit={sendMessage}
        >
          <textarea
            ref={composerRef}
            rows={1}
            placeholder="Message Corvus…"
            aria-label="Message Corvus"
            value={draft}
            disabled={sending}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                event.currentTarget.form?.requestSubmit()
              }
            }}
          />
          <button
            type="submit"
            className="send-button"
            disabled={sending || !draft.trim()}
            aria-label={sending ? 'Sending message' : 'Send message'}
          >
            {sending ? (
              <span className="send-spinner" />
            ) : (
              <span className="send-arrow">↑</span>
            )}
          </button>
        </form>
        {chatError && (
          <p className="chat-error" role="alert">
            {chatError}
          </p>
        )}
        </section>
      </div>

      {inspectOpen && (
        <button
          type="button"
          className="drawer-backdrop"
          aria-label="Close inspector"
          onClick={() => setInspectOpen(false)}
        />
      )}

      <aside className={`inspector ${inspectOpen ? 'open' : ''}`}>
        <header className="inspector-header">
          <div>
            <span className="eyebrow">MEMORY</span>
            <h2>Inspector</h2>
          </div>

          <button
            type="button"
            className="close-button"
            onClick={() => setInspectOpen(false)}
          >
            ×
          </button>
        </header>

        <nav className="inspect-tabs">
          <button className={tab === 'evidence' ? 'active' : ''} onClick={() => setTab('evidence')}>Evidence</button>
          <button className={tab === 'assertions' ? 'active' : ''} onClick={() => setTab('assertions')}>Assertions</button>
          <button className={tab === 'world' ? 'active' : ''} onClick={() => setTab('world')}>World</button>
        </nav>

        <section className="inspector-content">
          {tab === 'evidence' && (
            <div className="evidence-list">
              {evidence.map((item) => (
                <article className="evidence-item" key={item.id}>
                  <div className="evidence-meta">
                    <span>#{item.id}</span>
                    <span>{item.role}</span>
                    <span>{item.session_id}</span>
                  </div>
                  <p>{item.content}</p>
                  <time>{item.created_at}</time>
                </article>
              ))}
            </div>
          )}
          {tab === 'assertions' && <p>Assertions</p>}
          {tab === 'world' && <p>Current World</p>}
        </section>
      </aside>
    </main>
  )
}

export default App
