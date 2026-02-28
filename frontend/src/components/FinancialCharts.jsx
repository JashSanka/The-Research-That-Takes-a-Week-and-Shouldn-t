import React, { useState } from 'react';
import {
    BarChart, Bar, LineChart, Line, AreaChart, Area,
    RadarChart, Radar, PolarGrid, PolarAngleAxis,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, ReferenceLine,
} from 'recharts';

// ── Colour palette ────────────────────────────────────────────────────────────
const COLORS = {
    revenue: '#6366f1',
    profit: '#10b981',
    loss: '#ef4444',
    debt: '#f59e0b',
    equity: '#3b82f6',
    stock: '#8b5cf6',
    margin: '#14b8a6',
};

const verdictConfig = {
    Strong: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', dot: 'bg-green-500' },
    Moderate: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', dot: 'bg-yellow-400' },
    Weak: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', dot: 'bg-red-500' },
    Unknown: { bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-500', dot: 'bg-slate-400' },
};

// ── Shared tooltip ─────────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label, prefix = '', suffix = '' }) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-slate-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl">
            <p className="font-semibold mb-1">{label}</p>
            {payload.map((p, i) => (
                <p key={i} style={{ color: p.color }}>
                    {p.name}: {prefix}{p.value?.toLocaleString()}{suffix}
                </p>
            ))}
        </div>
    );
};

// ── Section wrapper ───────────────────────────────────────────────────────────
const ChartCard = ({ title, subtitle, children }) => (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
        <div className="mb-4">
            <h4 className="font-semibold text-slate-800 text-sm">{title}</h4>
            {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
        {children}
    </div>
);

// ── 1. Revenue vs Net Profit ──────────────────────────────────────────────────
function RevenueChart({ data, currency }) {
    const unit = currency === 'INR' ? 'Cr' : 'M';
    const formatted = [...data].reverse().map(d => ({
        year: d.year,
        Revenue: d.revenue,
        'Net Profit': d.net_profit,
    }));
    return (
        <ChartCard title="Revenue vs Net Profit" subtitle={`Annual · ${unit} ${currency}`}>
            <ResponsiveContainer width="100%" height={220}>
                <BarChart data={formatted} barCategoryGap="30%">
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip suffix={` ${unit}`} />} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="Revenue" fill={COLORS.revenue} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Net Profit" fill={COLORS.profit} radius={[4, 4, 0, 0]}
                        label={false}
                    />
                    <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 2" />
                </BarChart>
            </ResponsiveContainer>
        </ChartCard>
    );
}

// ── 2. Gross Margin % ─────────────────────────────────────────────────────────
function MarginChart({ data }) {
    const formatted = [...data].reverse()
        .filter(d => d.gross_margin != null)
        .map(d => ({ year: d.year, 'Gross Margin %': d.gross_margin }));

    if (!formatted.length) return null;
    return (
        <ChartCard title="Gross Margin Trend" subtitle="Annual %">
            <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={formatted}>
                    <defs>
                        <linearGradient id="marginGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={COLORS.margin} stopOpacity={0.3} />
                            <stop offset="95%" stopColor={COLORS.margin} stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} unit="%" domain={['auto', 'auto']} />
                    <Tooltip content={<CustomTooltip suffix="%" />} />
                    <Area type="monotone" dataKey="Gross Margin %" stroke={COLORS.margin}
                        fill="url(#marginGrad)" strokeWidth={2} dot={{ r: 4 }} />
                </AreaChart>
            </ResponsiveContainer>
        </ChartCard>
    );
}

// ── 3. Stock Price 1yr ────────────────────────────────────────────────────────
function StockChart({ data, currency }) {
    // Sample to ~52 weekly points for performance
    const sampled = data.filter((_, i) => i % 5 === 0);
    return (
        <ChartCard title="Stock Price — 1 Year" subtitle={`Daily close · ${currency}`}>
            <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={sampled}>
                    <defs>
                        <linearGradient id="stockGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={COLORS.stock} stopOpacity={0.25} />
                            <stop offset="95%" stopColor={COLORS.stock} stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="date" tick={{ fontSize: 9 }}
                        tickFormatter={d => d.slice(5)} interval={7} />
                    <YAxis tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area type="monotone" dataKey="close" stroke={COLORS.stock}
                        fill="url(#stockGrad)" strokeWidth={2} dot={false} name="Price" />
                </AreaChart>
            </ResponsiveContainer>
        </ChartCard>
    );
}

// ── 4. Debt vs Equity ────────────────────────────────────────────────────────
function DebtEquityChart({ data, currency }) {
    const unit = currency === 'INR' ? 'Cr' : 'M';
    const formatted = [...data].reverse()
        .filter(d => d.total_debt != null || d.total_equity != null)
        .map(d => ({ year: d.year, Debt: d.total_debt, Equity: d.total_equity }));

    if (!formatted.length) return null;
    return (
        <ChartCard title="Debt vs Equity" subtitle={`Annual · ${unit} ${currency}`}>
            <ResponsiveContainer width="100%" height={220}>
                <BarChart data={formatted} barCategoryGap="30%">
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip suffix={` ${unit}`} />} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Bar dataKey="Debt" fill={COLORS.debt} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Equity" fill={COLORS.equity} radius={[4, 4, 0, 0]} />
                </BarChart>
            </ResponsiveContainer>
        </ChartCard>
    );
}

// ── 5. VC Scorecard Radar + Cards ────────────────────────────────────────────
function VCScorecard({ scorecard, overallScore, verdict }) {
    const radarData = scorecard.map(s => ({ subject: s.dimension.split(' ')[0], score: s.score }));

    const verdictColor =
        verdict.includes('Strong') ? 'text-green-600' :
            verdict.includes('Investigate') ? 'text-yellow-600' :
                verdict.includes('Caution') ? 'text-orange-600' : 'text-red-600';

    return (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-5">
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                    <h4 className="font-semibold text-slate-800">VC Investment Scorecard</h4>
                    <p className="text-xs text-slate-400 mt-0.5">10-dimension analysis by AI VC Analyst</p>
                </div>
                <div className="text-right">
                    <p className="text-3xl font-bold text-slate-900">{overallScore}<span className="text-lg text-slate-400">/10</span></p>
                    <p className={`text-sm font-semibold ${verdictColor}`}>{verdict}</p>
                </div>
            </div>

            {/* Radar chart */}
            <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={radarData}>
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Radar name="Score" dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.25} />
                    <Tooltip formatter={(val) => [`${val}/10`, 'Score']} />
                </RadarChart>
            </ResponsiveContainer>

            {/* Dimension cards grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {scorecard.map((s) => {
                    const cfg = verdictConfig[s.verdict] || verdictConfig.Unknown;
                    return (
                        <div key={s.dimension} className={`rounded-xl border p-3 ${cfg.bg} ${cfg.border}`}>
                            <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-1.5">
                                    <div className={`w-2 h-2 rounded-full ${cfg.dot}`} />
                                    <span className="text-xs font-semibold text-slate-700">{s.dimension}</span>
                                </div>
                                <span className={`text-sm font-bold ${cfg.text}`}>{s.score}/10</span>
                            </div>
                            <p className="text-xs text-slate-500 leading-snug">{s.rationale}</p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ── Tracxn Intelligence Panel ───────────────────────────────────────────────
function TracxnPanel({ tracxn }) {
    if (!tracxn) return (
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-8 text-center">
            <p className="text-slate-400 text-sm">No Tracxn data available for this company.</p>
            <p className="text-slate-300 text-xs mt-1">Company may not be listed on tracxn.com</p>
        </div>
    );

    const stageBadge = tracxn.stage ? (
        <span className="bg-indigo-100 text-indigo-700 text-xs font-semibold px-2.5 py-0.5 rounded-full">{tracxn.stage}</span>
    ) : null;

    return (
        <div className="space-y-4">
            {/* About */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
                    <div>
                        <h4 className="font-semibold text-slate-800">About the Company</h4>
                        <p className="text-xs text-slate-400 mt-0.5">
                            Source: <a href={tracxn.source_url} target="_blank" rel="noreferrer"
                                className="text-indigo-500 hover:underline">tracxn.com</a>
                        </p>
                    </div>
                    {stageBadge}
                </div>
                <p className="text-sm text-slate-600 leading-relaxed">{tracxn.about}</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4">
                    {tracxn.founded_year && (
                        <div className="bg-slate-50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">Founded</p>
                            <p className="text-sm font-semibold text-slate-700">{tracxn.founded_year}</p>
                        </div>
                    )}
                    {tracxn.headquarters && (
                        <div className="bg-slate-50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">Headquarters</p>
                            <p className="text-sm font-semibold text-slate-700">{tracxn.headquarters}</p>
                        </div>
                    )}
                    {tracxn.total_funding && (
                        <div className="bg-slate-50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">Total Funding</p>
                            <p className="text-sm font-semibold text-indigo-600">{tracxn.total_funding}</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Key Metrics */}
            {tracxn.key_metrics?.length > 0 && (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                    <h4 className="font-semibold text-slate-800 mb-3">Key Metrics</h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                        {tracxn.key_metrics.map((m, i) => (
                            <div key={i} className="bg-gradient-to-br from-indigo-50 to-slate-50 border border-indigo-100 rounded-xl p-3">
                                <p className="text-xs text-slate-400 leading-tight">{m.label}</p>
                                <p className="text-sm font-bold text-slate-800 mt-0.5">{m.value}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Competitors */}
            {tracxn.competitors?.length > 0 && (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                    <h4 className="font-semibold text-slate-800 mb-3">Competitors & Alternatives</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {tracxn.competitors.map((c, i) => (
                            <div key={i} className="flex items-start gap-3 bg-slate-50 rounded-xl p-3 border border-slate-100">
                                <div className="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center shrink-0">
                                    <span className="text-xs font-bold text-indigo-600">{c.name[0]}</span>
                                </div>
                                <div className="min-w-0">
                                    <p className="text-sm font-semibold text-slate-800">
                                        {c.url ? (
                                            <a href={c.url} target="_blank" rel="noreferrer"
                                                className="hover:text-indigo-600">{c.name}</a>
                                        ) : c.name}
                                    </p>
                                    {c.description && (
                                        <p className="text-xs text-slate-500 mt-0.5 leading-snug">{c.description}</p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// ── Public company ratios banner ──────────────────────────────────────────────
function KeyRatiosBanner({ ratios, ticker, company, currency }) {
    const items = [
        { label: 'P/E Ratio', value: ratios?.pe_ratio?.toFixed(1) ?? '—' },
        { label: 'Market Cap', value: ratios?.market_cap_cr ? `${ratios.market_cap_cr?.toLocaleString()} ${currency === 'INR' ? 'Cr' : 'M'}` : '—' },
        { label: '52W High', value: ratios?.week_52_high?.toFixed(2) ?? '—' },
        { label: '52W Low', value: ratios?.week_52_low?.toFixed(2) ?? '—' },
        { label: 'Revenue Growth', value: ratios?.revenue_growth_yoy != null ? `${ratios.revenue_growth_yoy > 0 ? '+' : ''}${ratios.revenue_growth_yoy}%` : '—' },
        { label: 'Profit Margin', value: ratios?.profit_margin != null ? `${ratios.profit_margin?.toFixed(1)}%` : '—' },
    ];
    return (
        <div className="bg-gradient-to-r from-indigo-900 to-slate-900 rounded-2xl p-5 text-white">
            <div className="flex items-baseline justify-between flex-wrap gap-2 mb-4">
                <div>
                    <h4 className="font-bold text-lg">{company}</h4>
                    <p className="text-indigo-300 text-sm">{ticker} · {currency}</p>
                </div>
                <span className="text-xs text-indigo-300 bg-indigo-800 rounded-full px-3 py-1">Live via Yahoo Finance</span>
            </div>
            <div className="grid grid-cols-3 gap-3">
                {items.map(({ label, value }) => (
                    <div key={label} className="bg-white/10 rounded-xl p-3">
                        <p className="text-indigo-300 text-xs">{label}</p>
                        <p className="text-white font-bold text-sm mt-0.5">{value}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── Private startup banner ────────────────────────────────────────────────────
function PrivateBanner({ company, webIntel }) {
    const profile = webIntel?.company_profile;
    const quickFacts = [
        { label: 'Stage', value: profile?.stage ?? webIntel?.business_model ?? '—' },
        { label: 'Funding', value: profile?.total_funding ?? '—' },
        { label: 'Revenue', value: webIntel?.annual_revenue ?? '—' },
        { label: 'Employees', value: webIntel?.employee_count ?? '—' },
        { label: 'Valuation', value: webIntel?.valuation ?? '—' },
        { label: 'Industry', value: webIntel?.industry ?? '—' },
    ];
    return (
        <div className="bg-gradient-to-r from-violet-900 to-slate-900 rounded-2xl p-5 text-white">
            <div className="flex items-baseline justify-between flex-wrap gap-2 mb-4">
                <div>
                    <h4 className="font-bold text-lg">{company}</h4>
                    <p className="text-violet-300 text-sm">Private / Unlisted Company</p>
                </div>
                <span className="text-xs text-violet-300 bg-violet-800 rounded-full px-3 py-1">🔍 Web Intelligence</span>
            </div>
            <div className="grid grid-cols-3 gap-3">
                {quickFacts.map(({ label, value }) => (
                    <div key={label} className="bg-white/10 rounded-xl p-3">
                        <p className="text-violet-300 text-xs">{label}</p>
                        <p className="text-white font-bold text-sm mt-0.5">{value}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ── Web Intelligence panel (private company) ──────────────────────────────────
function WebIntelPanel({ webIntel, tracxn }) {
    const profile = webIntel?.company_profile || tracxn;
    if (!webIntel && !tracxn) return (
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-8 text-center">
            <p className="text-slate-400 text-sm">No structured data found for this company.</p>
        </div>
    );

    const allCompetitors = [
        ...(profile?.competitors || []),
    ].filter((c, i, arr) => arr.findIndex(x => x.name === c.name) === i);

    const allMetrics = [
        ...(profile?.key_metrics || []),
    ];

    return (
        <div className="space-y-4">
            {/* About */}
            {profile?.about && (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                    <h4 className="font-semibold text-slate-800 mb-2">About the Company</h4>
                    <p className="text-sm text-slate-600 leading-relaxed">{profile.about}</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4">
                        {profile.founded_year && <div className="bg-slate-50 rounded-xl p-3"><p className="text-xs text-slate-400">Founded</p><p className="text-sm font-semibold text-slate-700">{profile.founded_year}</p></div>}
                        {profile.headquarters && <div className="bg-slate-50 rounded-xl p-3"><p className="text-xs text-slate-400">HQ</p><p className="text-sm font-semibold text-slate-700">{profile.headquarters}</p></div>}
                        {profile.total_funding && <div className="bg-slate-50 rounded-xl p-3"><p className="text-xs text-slate-400">Funding</p><p className="text-sm font-semibold text-indigo-600">{profile.total_funding}</p></div>}
                    </div>
                </div>
            )}

            {/* Founders & Investors */}
            {(webIntel?.founders?.length > 0 || webIntel?.investors?.length > 0) && (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {webIntel.founders?.length > 0 && (
                            <div>
                                <h4 className="font-semibold text-slate-800 mb-2 text-sm">👤 Founders</h4>
                                <div className="flex flex-wrap gap-2">
                                    {webIntel.founders.map((f, i) => <span key={i} className="bg-indigo-50 text-indigo-700 text-xs font-medium px-2.5 py-1 rounded-full">{f}</span>)}
                                </div>
                            </div>
                        )}
                        {webIntel.investors?.length > 0 && (
                            <div>
                                <h4 className="font-semibold text-slate-800 mb-2 text-sm">💼 Investors</h4>
                                <div className="flex flex-wrap gap-2">
                                    {webIntel.investors.map((inv, i) => <span key={i} className="bg-green-50 text-green-700 text-xs font-medium px-2.5 py-1 rounded-full">{inv}</span>)}
                                </div>
                            </div>
                        )}
                    </div>
                    {webIntel?.recent_news && (
                        <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-xl">
                            <p className="text-xs font-semibold text-yellow-700 mb-0.5">📰 Latest News</p>
                            <p className="text-xs text-yellow-800">{webIntel.recent_news}</p>
                        </div>
                    )}
                </div>
            )}

            {/* Key Metrics */}
            {allMetrics.length > 0 && (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                    <h4 className="font-semibold text-slate-800 mb-3">Key Metrics</h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                        {allMetrics.map((m, i) => (
                            <div key={i} className="bg-gradient-to-br from-indigo-50 to-slate-50 border border-indigo-100 rounded-xl p-3">
                                <p className="text-xs text-slate-400">{m.label}</p>
                                <p className="text-sm font-bold text-slate-800 mt-0.5">{m.value}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Products */}
            {webIntel?.products?.length > 0 && (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                    <h4 className="font-semibold text-slate-800 mb-3">🛠 Products & Services</h4>
                    <div className="flex flex-wrap gap-2">
                        {webIntel.products.map((p, i) => <span key={i} className="bg-slate-100 text-slate-700 text-xs px-3 py-1 rounded-full border border-slate-200">{p}</span>)}
                    </div>
                </div>
            )}

            {/* Competitors */}
            {allCompetitors.length > 0 && (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
                    <h4 className="font-semibold text-slate-800 mb-3">Competitors & Alternatives</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {allCompetitors.map((c, i) => (
                            <div key={i} className="flex items-start gap-3 bg-slate-50 rounded-xl p-3 border border-slate-100">
                                <div className="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center shrink-0">
                                    <span className="text-xs font-bold text-indigo-600">{c.name?.[0]}</span>
                                </div>
                                <div>
                                    <p className="text-sm font-semibold text-slate-800">{c.name}</p>
                                    {c.description && <p className="text-xs text-slate-500 mt-0.5">{c.description}</p>}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// ── Main export ───────────────────────────────────────────────────────────────
export default function FinancialCharts({ data }) {
    const isPrivate = data?.is_private;
    const defaultTab = isPrivate ? 'intel' : 'financials';
    const [activeTab, setActiveTab] = useState(defaultTab);

    if (!data) return null;

    const { ticker, company, currency, yearly_financials: yf,
        stock_price_history: sp, key_ratios, vc_scorecard, overall_vc_score,
        investment_verdict, tracxn_data, web_intelligence } = data;

    const hasChartData = yf?.length > 0 || sp?.length > 0;

    const tabs = [
        ...(hasChartData ? [{ id: 'financials', label: '📊 Financial Charts' }] : []),
        { id: 'scorecard', label: '🎯 VC Scorecard' },
        { id: 'intel', label: '🔍 Company Intel' },
    ];

    return (
        <div className="space-y-4 mt-2">
            {/* Header banner — different style for private/public */}
            {isPrivate
                ? <PrivateBanner company={company} webIntel={web_intelligence} />
                : <KeyRatiosBanner ratios={key_ratios} ticker={ticker} company={company} currency={currency} />
            }

            {/* Tab switcher */}
            <div className="flex gap-2 flex-wrap">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${activeTab === tab.id
                                ? 'bg-indigo-600 text-white shadow'
                                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {activeTab === 'financials' && hasChartData && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {yf?.length > 0 && <RevenueChart data={yf} currency={currency} />}
                    {yf?.length > 0 && <MarginChart data={yf} />}
                    {sp?.length > 0 && <StockChart data={sp} currency={currency} />}
                    {yf?.length > 0 && <DebtEquityChart data={yf} currency={currency} />}
                </div>
            )}

            {activeTab === 'scorecard' && (
                <VCScorecard
                    scorecard={vc_scorecard || []}
                    overallScore={overall_vc_score}
                    verdict={investment_verdict}
                />
            )}

            {activeTab === 'intel' && (
                isPrivate
                    ? <WebIntelPanel webIntel={web_intelligence} tracxn={tracxn_data} />
                    : <TracxnPanel tracxn={tracxn_data} />
            )}
        </div>
    );
}
