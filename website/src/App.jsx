import React from 'react';
import { motion } from 'framer-motion';
import Hero from './sections/Hero';
import Features from './sections/Features';
import Comparison from './sections/Comparison';
import Skills from './sections/Skills';
import Install from './sections/Install';
import Architecture from './sections/Architecture';
import Footer from './sections/Footer';
import Navbar from './components/Navbar';
import UpdateBanner from './components/UpdateBanner';

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: 'easeOut' } },
};

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-white overflow-x-hidden">
      <Navbar />
      <UpdateBanner />
      <Hero />
      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={fadeUp}>
        <Features />
      </motion.div>
      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={fadeUp}>
        <Comparison />
      </motion.div>
      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={fadeUp}>
        <Skills />
      </motion.div>
      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={fadeUp}>
        <Install />
      </motion.div>
      <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, margin: '-100px' }} variants={fadeUp}>
        <Architecture />
      </motion.div>
      <Footer />
    </div>
  );
}
