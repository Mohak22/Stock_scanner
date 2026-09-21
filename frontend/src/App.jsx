import { useState } from 'react'
import './App.css'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import ResearchConfig from './components/ResearchConfig'
import ExperimentHistory from './components/experiments/ExperimentHistory'
import ExperimentDetail from './components/experiments/ExperimentDetail'

function App() {
    const [activePage, setActivePage] = useState('research')
    const [selectedExperimentId, setSelectedExperimentId] =
        useState(null)

    function openExperiment(experiment) {
        setSelectedExperimentId(
            experiment.experiment_id
        )
        setActivePage('experiment-detail')
    }

    function backToExperimentHistory() {
        setSelectedExperimentId(null)
        setActivePage('experiments')
    }

    return (
        <div className="app">

            <Sidebar
                activePage={activePage}
                setActivePage={setActivePage}
            />

            <div className="workspace">

                <TopBar />

                <main className="main-content">

                    {activePage === 'research' && (
                        <ResearchConfig />
                    )}

                    {activePage === 'experiments' && (
                        <ExperimentHistory
                            onOpenExperiment={
                                openExperiment
                            }
                        />
                    )}

                    {activePage === 'experiment-detail' &&
                        selectedExperimentId && (
                            <ExperimentDetail
                                experimentId={
                                    selectedExperimentId
                                }
                                onBack={
                                    backToExperimentHistory
                                }
                            />
                        )}

                </main>

            </div>

        </div>
    )
}

export default App