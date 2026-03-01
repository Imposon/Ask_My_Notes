import React from 'react';
import { AlertTriangle, Activity, CreditCard } from 'lucide-react';
import './AnomalyMetrics.css';

export default function AnomalyMetrics() {
    return (
        <div className="metrics-grid">
            <div className="glass-panel metric-card glow-anomaly">
                <div className="metric-header">
                    <AlertTriangle className="metric-icon anomaly-icon" size={20} />
                    <h4>Risk Score</h4>
                </div>
                <div className="metric-value anomaly-text">84<span className="metric-sub">/100</span></div>
                <p className="metric-desc">Critical anomalies detected in recent activity.</p>
            </div>

            <div className="glass-panel metric-card">
                <div className="metric-header">
                    <Activity className="metric-icon" size={20} />
                    <h4>Anomalies Found</h4>
                </div>
                <div className="metric-value">12</div>
                <p className="metric-desc">Out of 342 total transactions this month.</p>
            </div>

            <div className="glass-panel metric-card">
                <div className="metric-header">
                    <CreditCard className="metric-icon" size={20} />
                    <h4>Total Scanned</h4>
                </div>
                <div className="metric-value">₹4.2L</div>
                <p className="metric-desc">Volume processed across all accounts.</p>
            </div>
        </div>
    );
}
