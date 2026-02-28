import React from 'react';
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';

const STEPS = [
    "Query Decomposition",
    "Multi-Source Retrieval",
    "Credibility & Freshness Analysis",
    "Structured Intelligence Synthesis",
    "Final Report Generation"
];

export default function ProgressTracker({ currentStep }) {
    // currentStep is index 0 to 5. If 5, it means completed.

    return (
        <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-200 w-full max-w-xl mx-auto my-12">
            <h3 className="text-xl font-semibold text-slate-800 mb-6 text-center">Processing Intelligence</h3>

            <div className="flex flex-col gap-4">
                {STEPS.map((step, index) => {
                    const isCompleted = currentStep > index;
                    const isCurrent = currentStep === index;

                    return (
                        <div key={index} className={`flex items-center gap-4 p-3 rounded-lg ${isCurrent ? 'bg-blue-50' : ''}`}>
                            <div className="flex-shrink-0">
                                {isCompleted ? (
                                    <CheckCircle2 className="text-green-500" size={24} />
                                ) : isCurrent ? (
                                    <Loader2 className="text-blue-500 animate-spin" size={24} />
                                ) : (
                                    <Circle className="text-slate-300" size={24} />
                                )}
                            </div>
                            <span className={`font-medium ${isCompleted ? 'text-slate-800' : isCurrent ? 'text-blue-700' : 'text-slate-400'}`}>
                                {step}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
