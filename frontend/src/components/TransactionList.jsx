import React from 'react';
import { ShieldAlert, CheckCircle2 } from 'lucide-react';
import './TransactionList.css';

const mockTransactions = [
    { id: 1, date: '2023-12-05', desc: 'APPLE.COM/BILL', category: 'Entertainment', amount: 899, anomaly: false, reason: null },
    { id: 2, date: '2023-12-05', desc: 'SWIGGY INSTAMART', category: 'Food', amount: 450, anomaly: false, reason: null },
    { id: 3, date: '2023-12-05', desc: 'ROLEX BOUTIQUE', category: 'Shopping', amount: 750000, anomaly: true, reason: 'Amount significantly exceeds normal spending pattern in Shopping category.' },
    { id: 4, date: '2023-12-04', desc: 'UBER RIDES', category: 'Transport', amount: 320, anomaly: false, reason: null },
    { id: 5, date: '2023-12-04', desc: 'AMAZON PAY', category: 'Shopping', amount: 1200, anomaly: false, reason: null },
];

export default function TransactionList() {
    return (
        <div className="glass-panel tx-panel">
            <div className="tx-header">
                <h3>Recent Transactions</h3>
                <button className="view-all-btn">View All</button>
            </div>

            <div className="tx-table-container">
                <table className="tx-table">
                    <thead>
                        <tr>
                            <th>Status</th>
                            <th>Date</th>
                            <th>Description</th>
                            <th>Category</th>
                            <th className="text-right">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {mockTransactions.map((tx) => (
                            <tr key={tx.id} className={tx.anomaly ? 'tx-row-anomaly' : 'tx-row'}>
                                <td>
                                    {tx.anomaly ? (
                                        <ShieldAlert size={18} className="icon-alert" />
                                    ) : (
                                        <CheckCircle2 size={18} className="icon-safe" />
                                    )}
                                </td>
                                <td className="tx-date">{tx.date}</td>
                                <td>
                                    <div className="tx-desc-wrapper">
                                        <span className="tx-desc">{tx.desc}</span>
                                        {tx.anomaly && <span className="tx-reason">{tx.reason}</span>}
                                    </div>
                                </td>
                                <td>
                                    <span className="tx-cat-badge">{tx.category}</span>
                                </td>
                                <td className={`text-right tx-amount ${tx.anomaly ? 'amount-alert' : ''}`}>
                                    ₹{tx.amount.toLocaleString('en-IN')}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
