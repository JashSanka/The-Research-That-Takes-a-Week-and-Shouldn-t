import React from 'react';
import { AlertTriangle, TrendingUp, CheckCircle, Lightbulb } from 'lucide-react';

export default function ReportView({ report }) {
    if (!report) return null;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden w-full max-w-4xl mx-auto mb-8">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex justify-between items-center">
                <h2 className="text-xl font-bold text-slate-800">Intelligence Report</h2>
                <div className="flex items-center gap-2 bg-blue-100 px-3 py-1 rounded-full border border-blue-200">
                    <CheckCircle size={16} className="text-blue-600" />
                    <span className="text-sm font-semibold text-blue-800">{report.confidenceScore}% Confidence</span>
                </div>
            </div>

            <div className="p-6 space-y-8">
                {/* Executive Summary */}
                <section>
                    <h3 className="text-lg font-semibold text-slate-800 mb-2 border-b border-slate-100 pb-2">A. Executive Summary</h3>
                    <p className="text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-md border border-slate-100">
                        {report.executiveSummary}
                    </p>
                </section>

                {/* Key Insights */}
                <section>
                    <h3 className="text-lg font-semibold text-slate-800 mb-3 flex items-center gap-2 border-b border-slate-100 pb-2">
                        <Lightbulb size={20} className="text-yellow-500" />
                        B. Key Insights
                    </h3>
                    <ul className="list-disc pl-5 space-y-2 text-slate-700">
                        {report.insights.map((insight, idx) => (
                            <li key={idx}>{insight}</li>
                        ))}
                    </ul>
                </section>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Risks */}
                    <section className="bg-red-50 p-4 rounded-xl border border-red-100">
                        <h3 className="text-lg font-semibold text-red-800 mb-3 flex items-center gap-2">
                            <AlertTriangle size={20} className="text-red-500" />
                            C. Risks
                        </h3>
                        <ul className="list-disc pl-5 space-y-2 text-red-900/80">
                            {report.risks.map((risk, idx) => (
                                <li key={idx}>{risk}</li>
                            ))}
                        </ul>
                    </section>

                    {/* Opportunities */}
                    <section className="bg-emerald-50 p-4 rounded-xl border border-emerald-100">
                        <h3 className="text-lg font-semibold text-emerald-800 mb-3 flex items-center gap-2">
                            <TrendingUp size={20} className="text-emerald-500" />
                            D. Opportunities
                        </h3>
                        <ul className="list-disc pl-5 space-y-2 text-emerald-900/80">
                            {report.opportunities.map((opp, idx) => (
                                <li key={idx}>{opp}</li>
                            ))}
                        </ul>
                    </section>
                </div>

                {/* Contradictions */}
                {report.contradictions && report.contradictions.length > 0 && (
                    <section className="bg-orange-50 p-4 rounded-xl border border-orange-100 border-l-4 border-l-orange-400">
                        <h3 className="text-lg font-semibold text-orange-800 mb-2">E. Contradictions Detected</h3>
                        <div className="space-y-3">
                            {report.contradictions.map((contra, idx) => (
                                <div key={idx} className="bg-white p-3 rounded shadow-sm border border-orange-200">
                                    <p className="text-sm text-slate-700">{contra}</p>
                                </div>
                            ))}
                        </div>
                    </section>
                )}
            </div>
        </div>
    );
}
