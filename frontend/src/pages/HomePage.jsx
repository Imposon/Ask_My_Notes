import React from 'react';
import Hero from '../components/Hero';
import Sections from '../components/Sections';
import CTA from '../components/CTA';

export default function HomePage() {
    return (
        <main className="flex-grow pt-[80px]">
            <Hero />
            <Sections />
            <CTA />
        </main>
    );
}
