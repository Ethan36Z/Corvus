import { useState } from 'react'
import './App.css'

type Tab = 'evidence' | 'assertions' | 'world'

type Evidence = {
  id: number
  session_id: string
  role: string
  content: string
  created_at: string
}

function App() {
  const [inspectOpen, setInspectOpen] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [tab, setTab] = useState<Tab>('evidence')
  const [evidence, setEvidence] = useState<Evidence[]>([])

  async function openInspector() {
    const response = await fetch('/api/evidence')
    const data = await response.json()
    setEvidence(data)
    setInspectOpen(true)
  }

  return (
    <main className="corvus-app" data-theme={theme}>
      <header className="topbar">
        <div>
          <span className="eyebrow">CORVUS</span>
          <h1>Memory Playground</h1>
        </div>

        <div className="topbar-actions">
          <span className="status">● Local</span>

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
            onClick={openInspector}
          >
            Inspect
          </button>
        </div>
      </header>

      <section className="chat-panel">
        <div className="messages">
          <div className="welcome">
            <h2>Corvus</h2>
            <p>Persistent memory, locally.</p>
          </div>
        </div>

        <form className="composer">
          <textarea
            rows={2}
            placeholder="Message Corvus…"
            aria-label="Message Corvus"
          />
          <button type="submit">↑</button>
        </form>
      </section>

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
