import React from 'react';


export default function Sections() {
    return (
        <div className="bg-white">

            {/* 3. Secondary Explanatory Section */}
            <section id="how-it-works" className="py-24 md:py-32 px-6 max-w-[1400px] mx-auto text-center border-t border-[#EEEEEE]">
                <div className="max-w-[800px] mx-auto">
                    <h2 className="text-[32px] md:text-[48px] font-bold text-black leading-[1.1] mb-6 tracking-tight">
                        Stop reacting to old bank statements. Start proactively monitoring your financial behavior.
                    </h2>
                    <p className="text-[19px] text-[#555555] leading-[1.6]">
                        Traditional tools just show you lists of transactions. Vortex learns your specific behavioral patterns and creates a unique baseline to detect real anomalies, reducing false positives and financial risk.
                    </p>
                </div>
            </section>

            {/* 4. Alternating feature sections */}
            <section id="features" className="py-16 md:py-32 px-6 max-w-[1400px] mx-auto flex flex-col gap-32 md:gap-48 border-t border-[#EEEEEE]">

                {/* Feature 1 */}
                <div className="flex flex-col md:flex-row items-center gap-12 md:gap-24">
                    <div className="flex-1 space-y-6">
                        <span className="text-[13px] font-bold tracking-widest uppercase text-[#555555]">Real-Time Anomalies</span>
                        <h3 className="text-[32px] md:text-[48px] font-bold text-black leading-[1.1] tracking-tight">
                            Instantly spot the unexpected.
                        </h3>
                        <p className="text-[18px] text-[#555555] leading-[1.6]">
                            Get notified immediately when transactions deviate from your historical norms—whether by amount, merchant, geographic location, or time of day.
                        </p>
                        <ul className="space-y-3 pt-4">
                            <li className="flex items-center gap-3 text-[16px] text-[#555555]">
                                <span className="w-1.5 h-1.5 bg-black rounded-full"></span> Amount-Based Deviation
                            </li>
                            <li className="flex items-center gap-3 text-[16px] text-[#555555]">
                                <span className="w-1.5 h-1.5 bg-black rounded-full"></span> New Merchant Detection
                            </li>
                        </ul>
                    </div>
                    <div className="flex-1 w-full aspect-square md:aspect-[4/3] bg-[#F9F9F9] rounded-[24px] md:rounded-[40px] flex items-center justify-center p-8 border border-[#EEEEEE]">
                        {/* Abstract Mock */}
                        <div className="w-full max-w-[320px] bg-white rounded-[20px] shadow-sm border border-[#EEEEEE] p-6 space-y-4">
                            <div className="w-1/3 h-3 bg-[#EEEEEE] rounded-full"></div>
                            <div className="w-full h-12 bg-[#F9F9F9] rounded-lg"></div>
                            <div className="w-full h-12 bg-black rounded-lg opacity-5"></div>
                            <div className="w-2/3 h-12 bg-[#F9F9F9] rounded-lg"></div>
                        </div>
                    </div>
                </div>

                {/* Feature 2 (Reversed) */}
                <div className="flex flex-col md:flex-row-reverse items-center gap-12 md:gap-24">
                    <div className="flex-1 space-y-6">
                        <span className="text-[13px] font-bold tracking-widest uppercase text-[#555555]">Explainable AI</span>
                        <h3 className="text-[32px] md:text-[48px] font-bold text-black leading-[1.1] tracking-tight">
                            Intelligence you can understand.
                        </h3>
                        <p className="text-[18px] text-[#555555] leading-[1.6]">
                            No black-box guesses. Every anomaly is assigned a precise risk score from 1-100, complete with a plain-English explanation of why it was flagged.
                        </p>
                        <ul className="space-y-3 pt-4">
                            <li className="flex items-center gap-3 text-[16px] text-[#555555]">
                                <span className="w-1.5 h-1.5 bg-black rounded-full"></span> 0-100 Risk Scoring
                            </li>
                            <li className="flex items-center gap-3 text-[16px] text-[#555555]">
                                <span className="w-1.5 h-1.5 bg-black rounded-full"></span> Human-Readable Reasons
                            </li>
                        </ul>
                    </div>
                    <div className="flex-1 w-full aspect-square md:aspect-[4/3] bg-[#F9F9F9] rounded-[24px] md:rounded-[40px] flex items-center justify-center p-8 border border-[#EEEEEE]">
                        {/* Abstract Mock */}
                        <div className="w-full max-w-[320px] bg-white rounded-[20px] shadow-sm border border-[#EEEEEE] p-8 text-center space-y-6">
                            <div className="text-[64px] font-bold text-black leading-none">84</div>
                            <div className="w-3/4 h-3 bg-[#EEEEEE] rounded-full mx-auto"></div>
                            <div className="w-full h-2 bg-[#EEEEEE] rounded-full mx-auto"></div>
                        </div>
                    </div>
                </div>

            </section>

            {/* 5. Highlight section */}
            <section className="py-32 md:py-48 px-6 bg-[#F9F9F9] border-y border-[#EEEEEE] text-center">
                <div className="max-w-[1000px] mx-auto">
                    <h2 className="text-[40px] md:text-[64px] font-bold text-black leading-[1.1] tracking-tight">
                        Designed for clarity. <br className="hidden md:block" />Built for financial security.
                    </h2>
                </div>
            </section>

        </div>
    );
}
