import React from 'react';
import { UploadCloud } from 'lucide-react';
import './UploadSection.css';

export default function UploadSection() {
    return (
        <div className="glass-panel upload-panel">
            <div className="upload-header">
                <h3>Import Statement</h3>
                <p className="upload-subtitle">Upload CSV to detect anomalies.</p>
            </div>

            <div className="dropzone">
                <UploadCloud size={40} className="upload-icon" />
                <p>Drag & drop your file here</p>
                <span className="upload-actions">or <button className="browse-btn">browse files</button></span>
            </div>
        </div>
    );
}
