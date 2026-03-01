import React from 'react';

export default function Footer() {
    return (
        <footer className="bg-[#F9F9F9] pt-20 pb-12 border-t border-[#EEEEEE] px-6">
            <div className="max-w-[1400px] mx-auto">

                {/* 4-column grid */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-16">

                    {/* Col 1 */}
                    <div className="col-span-1">
                        <div className="flex items-center gap-2 mb-6">
                            <div className="w-5 h-5 bg-black rounded-sm flex items-center justify-center">
                                <span className="text-white font-bold text-[10px]">V</span>
                            </div>
                            <span className="font-bold text-base tracking-tight text-black">Vortex</span>
                        </div>
                        <p className="text-[14px] text-[#555555] leading-[1.6]">
                            AI-powered transaction monitoring.<br />
                            Detect the unexpected instantly.
                        </p>
                    </div>

                    {/* Col 2 */}
                    <div>
                        <h4 className="text-[13px] font-bold uppercase tracking-widest text-black mb-6">Product</h4>
                        <ul className="space-y-4">
                            <li><a href="#" className="text-[14px] text-[#555555] hover:text-black transition-colors">Features</a></li>
                            <li><a href="#" className="text-[14px] text-[#555555] hover:text-black transition-colors">Pricing</a></li>
                            <li><a href="#" className="text-[14px] text-[#555555] hover:text-black transition-colors">Security</a></li>
                            <li><a href="#" className="text-[14px] text-[#555555] hover:text-black transition-colors">Changelog</a></li>
                        </ul>
                    </div>

                    {/* Col 3 */}
                    <div>
                        <h4 className="text-[13px] font-bold uppercase tracking-widest text-black mb-6">Company</h4>
                        <ul className="space-y-4">
                            <li><a href="#" className="text-[14px] text-[#555555] hover:text-black transition-colors">About Us</a></li>
                            <li><a href="#" className="text-[14px] text-[#555555] hover:text-black transition-colors">Careers</a></li>
                            <li><a href="#" className="text-[14px] text-[#555555] hover:text-black transition-colors">Blog</a></li>
                            <li><a href="#" className="text-[14px] text-[#555555] hover:text-black transition-colors">Contact</a></li>
                        </ul>
                    </div>

                    {/* Col 4 */}
                    <div>
                        <h4 className="text-[13px] font-bold uppercase tracking-widest text-black mb-6">Legal</h4>
                        <ul className="space-y-4">
                            <li><a href="#" className="text-[14px] text-[#555555] hover:text-black transition-colors">Privacy Policy</a></li>
                            <li><a href="#" className="text-[14px] text-[#555555] hover:text-black transition-colors">Terms of Service</a></li>
                        </ul>
                    </div>

                </div>

                {/* Bottom */}
                <div className="pt-8 border-t border-[#EEEEEE] flex flex-col md:flex-row items-center justify-between gap-4">
                    <p className="text-[13px] text-[#555555]">
                        © {new Date().getFullYear()} Vortex, Inc. All rights reserved.
                    </p>
                    <div className="flex gap-4">
                        {/* Social icons placeholder */}
                        <div className="w-5 h-5 bg-[#EEEEEE] rounded-full"></div>
                        <div className="w-5 h-5 bg-[#EEEEEE] rounded-full"></div>
                        <div className="w-5 h-5 bg-[#EEEEEE] rounded-full"></div>
                    </div>
                </div>

            </div>
        </footer>
    );
}
