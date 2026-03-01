import React from 'react';
import './Dashboard.css';
import UploadSection from './UploadSection';
import AnomalyMetrics from './AnomalyMetrics';
import FinancialChart from './FinancialChart';
import TransactionList from './TransactionList';

export default function Dashboard() {
    return (
        <div className="dashboard-container">
            <header className="dashboard-header">
                <div className="logo-area">
                    <div className="logo-mark">V</div>
                    <h1>Vortex Intelligence</h1>
                </div>
                <nav>
                    <button className="nav-btn active">Overview</button>
                    <button className="nav-btn">Upload Data</button>
                </nav>
            </header>

            <main className="dashboard-main">
                <section className="top-section">
                    <AnomalyMetrics />
                    <UploadSection />
                </section>

                <section className="middle-section">
                    <FinancialChart />
                </section>

                <section className="bottom-section">
                    <TransactionList />
                </section>
            </main>
        </div>
    );
}
