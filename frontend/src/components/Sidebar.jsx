import React from 'react';
import { History, Clock } from 'lucide-react';

export default function Sidebar({ history }) {
    return (
        <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col h-full border-r border-slate-800">
            <div className="p-4 border-b border-slate-800">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                    <History size={20} />
                    History
                </h2>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {history.length === 0 ? (
                    <p className="text-sm text-slate-500">No past queries yet.</p>
                ) : (
                    history.map((item, idx) => (
                        <div key={idx} className="bg-slate-800 p-3 rounded-md hover:bg-slate-700 cursor-pointer transition-colors">
                            <p className="text-sm text-slate-200 line-clamp-2 mb-2">{item.query}</p>
                            <div className="flex items-center justify-between text-xs text-slate-400">
                                <span className="flex items-center gap-1"><Clock size={12} /> {item.time}</span>
                                <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${item.score > 80 ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'}`}>
                                    {item.score}% Conf.
                                </span>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </aside>
    );
}
