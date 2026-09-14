import './App.css'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import ResearchConfig from './components/ResearchConfig'

function App() {
  return (
    <div className="app">

      <Sidebar />

      <div className="workspace">

        <TopBar />

        <main className="main-content">
          <ResearchConfig />
        </main>

      </div>

    </div>
  )
}

export default App