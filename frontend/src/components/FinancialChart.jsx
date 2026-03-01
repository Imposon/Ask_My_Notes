import React from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceDot } from 'recharts';
import './FinancialChart.css';

const mockData = [
    { date: '12/01', amount: 1200, anomaly: false },
    { date: '12/02', amount: 900, anomaly: false },
    { date: '12/03', amount: 1500, anomaly: false },
    { date: '12/04', amount: 800, anomaly: false },
    { date: '12/05', amount: 7500, anomaly: true, reason: 'unusual spike' },
    { date: '12/06', amount: 1100, anomaly: false },
    { date: '12/07', amount: 1000, anomaly: false },
];

export default function FinancialChart() {
    return (
        <div className="glass-panel chart-panel">
            <div className="chart-header">
                <h3>Spending Trend</h3>
                <span className="chart-badge">Last 7 Days</span>
            </div>

            <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={mockData} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#1FA6F3" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#1FA6F3" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                        <XAxis dataKey="date" stroke="#8F8F94" fontSize={12} tickLine={false} axisLine={false} dy={10} />
                        <YAxis stroke="#8F8F94" fontSize={12} tickLine={false} axisLine={false} dx={-10} tickFormatter={(val) => `₹${val}`} />
                        <Tooltip
                            contentStyle={{ backgroundColor: 'rgba(20, 20, 22, 0.9)', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                            itemStyle={{ color: '#1FA6F3' }}
                            labelStyle={{ color: '#8F8F94', marginBottom: '4px' }}
                        />
                        <Area type="monotone" dataKey="amount" stroke="#1FA6F3" strokeWidth={3} fillOpacity={1} fill="url(#colorAmount)" activeDot={{ r: 6, stroke: '#1FA6F3', strokeWidth: 2, fill: '#0A0A0B' }} />

                        {mockData.map((entry, index) => (
                            entry.anomaly && (
                                <ReferenceDot key={`anomaly-${index}`} x={entry.date} y={entry.amount} r={6} fill="#FF3B30" stroke="#FF3B30" strokeWidth={2} />
                            )
                        ))}
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
