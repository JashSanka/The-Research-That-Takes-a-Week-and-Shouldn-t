import React, { useState } from 'react';
import { Search, Settings2, Activity } from 'lucide-react';

export default function QueryInput({ onGenerate }) {
    const [query, setQuery] = useState('');
    const [depth, setDepth] = useState('Advanced');
    const [monitoring, setMonitoring] = useState(false);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (query.trim()) {
            onGenerate(query, depth);
        }
    };

    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 w-full max-w-3xl mx-auto">
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                <div className="relative">
                    <label htmlFor="query" className="sr-only">Enter your research question</label>
                    <textarea
                        id="query"
                        className="w-full text-lg p-4 pb-12 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                        rows={3}
                        placeholder="What are the risks of AI regulation for Indian fintech startups?"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                    <div className="absolute bottom-3 right-3">
                        <button
                            type="submit"
                            disabled={!query.trim()}
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-medium rounded-md flex items-center gap-2 transition-colors"
                        >
                            <Search size={18} />
                            Generate Report
                        </button>
                    </div>
                </div>

                <div className="flex items-center justify-between mt-2 pt-4 border-t border-slate-100">
                    <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer hover:text-slate-900">
                        <input
                            type="checkbox"
                            checked={monitoring}
                            onChange={(e) => setMonitoring(e.target.checked)}
                            className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        />
                        <Activity size={16} />
                        <span>Enable Continuous Monitoring</span>
                    </label>

                    <div className="flex items-center gap-2 text-sm text-slate-600">
                        <Settings2 size={16} />
                        <span className="mr-2">Depth:</span>
                        <select
                            value={depth}
                            onChange={(e) => setDepth(e.target.value)}
                            className="bg-slate-50 border border-slate-200 text-slate-700 rounded-md px-3 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option>Basic</option>
                            <option>Advanced</option>
                        </select>
                    </div>
                </div>
            </form>
        </div>
    );
}
