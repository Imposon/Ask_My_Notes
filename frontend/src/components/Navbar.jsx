import React from 'react';

export default function Navbar() {
    return (
        <nav className="fixed top-0 w-full z-50 bg-white/90 backdrop-blur-sm border-b border-[#EEEEEE]">
            <div className="max-w-[1400px] mx-auto px-6 h-20 flex items-center justify-between">

                {/* Logo Left */}
                <div className="flex-shrink-0 flex items-center gap-2">
                    <div className="w-6 h-6 bg-black rounded-sm flex items-center justify-center">
                        <span className="text-white font-bold text-xs">V</span>
                    </div>
                    <span className="font-bold text-lg tracking-tight">Vortex</span>
                </div>

                {/* Centered Nav Links */}
                <div className="hidden md:flex flex-1 justify-center space-x-10">
                    <a href="#features" className="text-[15px] font-medium text-[#555555] hover:text-black transition-colors">Features</a>
                    <a href="#how-it-works" className="text-[15px] font-medium text-[#555555] hover:text-black transition-colors">How It Works</a>
                    <a href="#pricing" className="text-[15px] font-medium text-[#555555] hover:text-black transition-colors">Pricing</a>
                    <a href="#about" className="text-[15px] font-medium text-[#555555] hover:text-black transition-colors">About</a>
                    <a href="#contact" className="text-[15px] font-medium text-[#555555] hover:text-black transition-colors">Contact</a>
                </div>

                {/* CTA Button Right */}
                <div className="flex-shrink-0 flex items-center">
                    <button className="bg-black text-white px-6 py-3 rounded-full text-[15px] font-medium hover:bg-gray-800 transition-colors">
                        Try Now
                    </button>
                </div>

            </div>
        </nav>
    );
}
