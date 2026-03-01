import React from 'react';


export default function DashboardPage() {
    return (
        <main className="flex-grow pt-32 px-6 max-w-[1400px] mx-auto min-h-screen">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <h1 className="text-4xl font-bold mb-8">Intelligence Dashboard</h1>
                <div className="bg-[#F9F9F9] border border-[#EEEEEE] rounded-[24px] p-12 text-center text-[#555555]">
                    <p className="text-xl">Welcome to your Vortex Dashboard.</p>
                    <p className="mt-4">Connect your bank accounts to begin anomaly analysis.</p>
                </div>
            </motion.div>
        </main>
    );
}
