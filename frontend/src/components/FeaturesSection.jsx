import React from 'react';
import { Activity, BellRing, Target, Shield, Lock, TrendingUp } from 'lucide-react';

const features = [
    {
        icon: <Activity className="w-6 h-6 text-brand-cyan" />,
        title: 'Behavioral Baselining',
        desc: 'Vortex learns your unique spending habits, establishing a baseline of normal behavior to reduce false positives.',
    },
    {
        icon: <BellRing className="w-6 h-6 text-brand-red" />,
        title: 'Anomaly Alerts',
        desc: 'Get notified immediately when transactions deviate from your historical norms—whether by amount, merchant, or location.',
    },
    {
        icon: <Target className="w-6 h-6 text-purple-400" />,
        title: 'Explainable AI',
        desc: 'No black-box guesses. Every anomaly comes with a clear, readable explanation of why it was flagged.',
    },
    {
        icon: <TrendingUp className="w-6 h-6 text-emerald-400" />,
        title: 'Trend Analysis',
        desc: 'Visualize your long-term financial shifts with beautiful, intuitive charts tracking your cash flow.',
    },
    {
        icon: <Shield className="w-6 h-6 text-blue-400" />,
        title: 'Multi-Format Support',
        desc: 'Upload CSVs or PDFs seamlessly. Our standardizer parses and normalizes formats from any major bank.',
    },
    {
        icon: <Lock className="w-6 h-6 text-gray-400" />,
        title: 'Complete Privacy',
        desc: 'Your financial data is processed securely and is never sold. Vortex runs isolated for your privacy.',
    }
];

export default function FeaturesSection() {
    return (
        <section id="features" className="py-24 bg-brand-dark/50 border-t border-white/5 relative z-10">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

                <div className="text-center max-w-3xl mx-auto mb-16">
                    <h2 className="text-3xl md:text-5xl font-bold font-heading text-white tracking-tight mb-4">
                        Intelligence beyond <span className="text-gray-500">raw data.</span>
                    </h2>
                    <p className="text-lg text-gray-400 font-light">
                        Traditional tools just show you lists of transactions. Vortex transforms those rows into explainable, proactive behavioral intelligence.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {features.map((feature, idx) => (
                        <div
                            key={idx}
                            className="glass p-8 rounded-2xl hover:bg-white/5 transition-all duration-300 group border border-white/5 hover:border-white/20"
                        >
                            <div className="w-12 h-12 rounded-lg bg-white/5 flex items-center justify-center mb-6 border border-white/10 group-hover:scale-110 group-hover:bg-white/10 transition-all">
                                {feature.icon}
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-3 font-heading tracking-wide">
                                {feature.title}
                            </h3>
                            <p className="text-gray-400 text-sm leading-relaxed font-light">
                                {feature.desc}
                            </p>
                        </div>
                    ))}
                </div>

            </div>
        </section>
    );
}
