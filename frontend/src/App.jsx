import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import QueryInput from './components/QueryInput';
import ProgressTracker from './components/ProgressTracker';
import ReportView from './components/ReportView';
import SourceList from './components/SourceList';

const MOCK_HISTORY = [];

const MOCK_REPORT = {
    confidenceScore: 88,
    executiveSummary: "AI regulation in India presents a dual-edged sword for fintech startups. While clearer guidelines on data privacy (DPDP Act) provide operational certainty, compliance costs will disproportionately affect early-stage companies. The push for AI sovereignty opens opportunities for localized models, but strict audits may slow deployment.",
    insights: [
        "Compliance costs for AI governance are projected to increase operating expenses by 15-20% for early-stage fintechs.",
        "RBI's focus on algorithmic fairness is driving a shift from \"black-box\" LLMs to explainable AI (XAI) models in credit scoring.",
        "B2B fintechs providing compliance-as-a-service are experiencing a surge in demand."
    ],
    risks: [
        "Steep fines under the new Digital Personal Data Protection (DPDP) Act for non-compliant AI training data.",
        "Prolonged approval cycles for new AI-driven financial products.",
        "Potential bias in legacy financial datasets leading to algorithmic discrimination penalties."
    ],
    opportunities: [
        "Development of localized, Indic-language financial LLMs compliant with data localization mandates.",
        "Pioneering \"Explainable AI\" solutions tailored for RBI regulatory frameworks.",
        "Partnering with traditional banks to accelerate their AI compliance transitions."
    ],
    contradictions: [
        "Source A (TechCrunch) suggests regulations will stifle innovation, while Source B (GovPolicy Report) argues clear frameworks will actually boost foreign direct investment.",
        "Estimates on compliance cost increases vary drastically wildly between 5% and 30% depending on the source."
    ]
};

const MOCK_SOURCES = [
    { title: "RBI Guidelines on Algorithmic Trading", domain: "rbi.org.in", credibility: 0.95, date: "Jan 2026", link: "#" },
    { title: "The Cost of Compliance for AI Startups", domain: "economictimes.indiatimes.com", credibility: 0.88, date: "Dec 2025", link: "#" },
    { title: "VC Trends in Indian Fintech", domain: "techcrunch.com", credibility: 0.82, date: "Feb 2026", link: "#" },
    { title: "Opinion: Overregulation kills innovation", domain: "fintechblog.xyz", credibility: 0.45, date: "Nov 2025", link: "#" }
];

function App() {
    const [status, setStatus] = useState('idle'); // 'idle' | 'generating' | 'done'
    const [step, setStep] = useState(0);

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
            <Sidebar history={MOCK_HISTORY} />

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
                            <ReportView report={MOCK_REPORT} />
                            <SourceList sources={MOCK_SOURCES} />

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
