import React from 'react';

import { Link } from 'react-router-dom';

export default function LoginPage() {
    return (
        <main className="flex-grow flex items-center justify-center min-h-screen bg-[#F9F9F9] px-6">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-white border border-[#EEEEEE] rounded-[24px] p-10 max-w-md w-full shadow-sm text-center"
            >
                <div className="flex items-center justify-center gap-2 mb-8">
                    <div className="w-8 h-8 bg-black rounded-sm flex items-center justify-center">
                        <span className="text-white font-bold text-sm">V</span>
                    </div>
                    <span className="font-bold text-xl tracking-tight">Vortex</span>
                </div>

                <h1 className="text-2xl font-bold mb-6">Welcome Back</h1>

                <div className="space-y-4">
                    <input type="email" placeholder="Email Address" className="w-full bg-[#F9F9F9] border border-[#EEEEEE] rounded-lg px-4 py-3 focus:outline-none focus:border-black" />
                    <input type="password" placeholder="Password" className="w-full bg-[#F9F9F9] border border-[#EEEEEE] rounded-lg px-4 py-3 focus:outline-none focus:border-black" />
                    <button className="w-full bg-black text-white rounded-full py-3 font-semibold hover:bg-gray-800 transition">Log In</button>
                </div>

                <p className="mt-6 text-sm text-[#555555]">
                    Don't have an account? <Link to="/dashboard" className="text-black font-semibold hover:underline">Sign up</Link>
                </p>
            </motion.div>
        </main>
    );
}
