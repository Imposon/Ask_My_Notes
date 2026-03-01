import React from 'react';
import { Link } from 'react-router-dom';

export default function CTA() {
    return (
        <section className="py-24 md:py-32 bg-black text-center px-6 border-b border-[#222]">
            <div className="max-w-[800px] mx-auto">
                <h2 className="text-[40px] md:text-[56px] font-bold text-white leading-[1.1] tracking-tight mb-10">
                    Ready to secure your financial future?
                </h2>

                <Link to="/dashboard" className="bg-white text-black px-10 py-5 rounded-full text-[17px] font-semibold hover:bg-gray-100 transition-colors inline-block">
                    Start Your Free Trial
                </Link>
            </div>
        </section>
    );
}
