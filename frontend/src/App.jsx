import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import QueryInput from './components/QueryInput';
import ProgressTracker from './components/ProgressTracker';
import ReportView from './components/ReportView';
import SourceList from './components/SourceList';

function App() {
    const [status, setStatus] = useState('idle'); // 'idle' | 'generating' | 'done'
    const [step, setStep] = useState(0);
    const [report, setReport] = useState(null);
    const [sources, setSources] = useState([]);
    const [history, setHistory] = useState([]);

    const handleGenerate = (query, depth) => {
        setStatus('generating');
        setStep(0);

        // Simulate generation process steps
        let currentStep = 0;
        const interval = setInterval(() => {
            currentStep++;
            setStep(currentStep);

            if (currentStep >= 5) {
                clearInterval(interval);
                setTimeout(() => setStatus('done'), 800);
            }
        }, 1200); // 1.2s per step for dramatic effect
    };

    return (
        <div className="flex h-screen bg-slate-100 overflow-hidden font-sans">
            <Sidebar history={history} />

            <main className="flex-1 overflow-y-auto w-full relative">
                {/* Header */}
                <header className="bg-white border-b border-slate-200 sticky top-0 z-10 px-8 py-4">
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-700 to-indigo-600 bg-clip-text text-transparent">
                        InsightEngine
                    </h1>
                    <p className="text-sm text-slate-500">Autonomous Research Intelligence Layer</p>
                </header>

                <div className="p-8 max-w-5xl mx-auto pb-24 space-y-8">

                    {/* Always show query input unless generating? Or keep it at top always */}
                    {status === 'idle' && (
                        <div className="mt-12">
                            <h2 className="text-3xl font-bold text-center text-slate-800 mb-8">What do you want to research today?</h2>
                            <QueryInput onGenerate={handleGenerate} />
                        </div>
                    )}

                    {status === 'generating' && (
                        <div className="mt-8 flex flex-col items-center">
                            <QueryInput onGenerate={() => { }} />
                            {/* Keep disabled input above for context */}
                            <ProgressTracker currentStep={step} />
                        </div>
                    )}

                    {status === 'done' && (
                        <div className="space-y-12 animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out mt-6">
                            {report && <ReportView report={report} />}
                            {sources.length > 0 && <SourceList sources={sources} />}

                            <div className="flex justify-center mt-8 pb-8">
                                <button
                                    onClick={() => setStatus('idle')}
                                    className="px-6 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 font-medium rounded-md transition-colors"
                                >
                                    Start New Research
                                </button>
                            </div>
                        </div>
                    )}

                </div>
            </main>
        </div>
    );
}

export default App;
