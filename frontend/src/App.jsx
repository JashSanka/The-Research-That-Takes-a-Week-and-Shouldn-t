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

    const handleGenerate = async (query, depth) => {
        setStatus('generating');
        setStep(1);

        let currentStep = 1;
        const interval = setInterval(() => {
            if (currentStep < 4) {
                currentStep++;
                setStep(currentStep);
            }
        }, 4000);

        try {
            const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
            const response = await fetch(`${BACKEND_URL}/api/v1/research/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });

            if (!response.ok) {
                throw new Error("Server Error");
            }

            const data = await response.json();
            const r = data.report;

            clearInterval(interval);
            setStep(5);

            const allContradictions = [];
            const allSources = [];
            const seenUrls = new Set();

            if (r.senior_analysis) {
                r.senior_analysis.forEach(analysis => {
                    if (analysis.contradictions) {
                        analysis.contradictions.forEach(c => allContradictions.push(`Conflict: ${c.claim_a} vs ${c.claim_b}. Stronger: ${c.stronger_signal}`));
                    }

                    const evals = {};
                    if (analysis.source_evaluations) {
                        analysis.source_evaluations.forEach(e => evals[e.url] = e);
                    }

                    if (analysis.sources) {
                        analysis.sources.forEach(s => {
                            if (!seenUrls.has(s.url)) {
                                seenUrls.add(s.url);
                                const ev = evals[s.url] || {};
                                let domain = ev.domain_type;
                                if (!domain) {
                                    try { domain = new URL(s.url).hostname.replace('www.', ''); } catch (e) { domain = 'web'; }
                                }
                                allSources.push({
                                    title: s.title,
                                    domain: domain,
                                    credibility: ev.credibility_score ? (ev.credibility_score / 10) : 0.8,
                                    date: s.published_date || "Recent",
                                    link: s.url
                                });
                            }
                        });
                    }
                });
            }

            setReport({
                confidenceScore: r.risk_assessment ? Math.round(r.risk_assessment.confidence_score * 10) : 80,
                executiveSummary: r.strategy_report?.executive_summary || "Report generated without summary.",
                insights: r.strategy_report?.key_findings?.map(kf => typeof kf === 'string' ? kf : kf.finding) || [],
                risks: r.strategy_report?.risks_and_uncertainties?.map(ru => typeof ru === 'string' ? ru : ru.risk) || [],
                opportunities: r.strategy_report?.strategic_implications || [],
                contradictions: allContradictions.length > 0 ? allContradictions : ["No major contradictions found."]
            });
            setSources(allSources);

            setTimeout(() => setStatus('done'), 800);

        } catch (error) {
            console.error("Fetch error:", error);
            clearInterval(interval);
            alert("Error generating report. Make sure your API keys are added in backend/.env!");
            setStatus('idle');
            setStep(0);
        }
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
