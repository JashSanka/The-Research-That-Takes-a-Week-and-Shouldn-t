import React from 'react';
import { ExternalLink, ShieldCheck } from 'lucide-react';

export default function SourceList({ sources }) {
    if (!sources || sources.length === 0) return null;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden w-full max-w-4xl mx-auto">
            <div className="bg-slate-800 px-6 py-3 border-b border-slate-700">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    <ShieldCheck size={18} className="text-blue-400" />
                    Source Transparency Panel
                </h3>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-slate-50 text-slate-600 text-sm uppercase tracking-wider border-b border-slate-200">
                            <th className="p-4 font-medium">Source Title</th>
                            <th className="p-4 font-medium hidden sm:table-cell">Domain</th>
                            <th className="p-4 font-medium text-center">Credibility</th>
                            <th className="p-4 font-medium text-center hidden md:table-cell">Freshness</th>
                            <th className="p-4 font-medium text-right">Link</th>
                        </tr>
                    </thead>
                    <tbody className="text-slate-700 text-sm">
                        {sources.map((source, idx) => (
                            <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                                <td className="p-4 font-medium text-slate-900">{source.title}</td>
                                <td className="p-4 text-slate-500 hidden sm:table-cell">{source.domain}</td>
                                <td className="p-4 text-center">
                                    <span className={`px-2 py-1 rounded text-xs font-semibold ${source.credibility >= 0.8 ? 'bg-green-100 text-green-800' :
                                            source.credibility >= 0.5 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'
                                        }`}>
                                        {(source.credibility * 100).toFixed(0)}%
                                    </span>
                                </td>
                                <td className="p-4 text-center text-slate-500 hidden md:table-cell">{source.date}</td>
                                <td className="p-4 text-right">
                                    <a href={source.link} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 hover:underline">
                                        View <ExternalLink size={14} />
                                    </a>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
