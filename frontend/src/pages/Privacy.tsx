import { Link } from 'react-router-dom';
import { ArrowLeft, ShieldCheck, Database, Clock, Lock } from 'lucide-react';
import { Footer } from '../components/Footer';

export function Privacy() {
  return (
    <div className="min-h-screen bg-[#0c0c0e] text-[#f2f2f0] flex flex-col justify-between">
      {/* Simple Top Navigation */}
      <header className="h-16 border-b border-[rgba(255,255,255,0.08)] bg-[#0c0c0e]/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
        <Link
          to="/"
          className="flex items-center gap-3 transition-transform duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6a3d]"
        >
          <img src="/logo-dark-bg.svg" alt="CleanIQ" className="h-8 w-auto object-contain" />
        </Link>

        <Link
          to="/"
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl border border-[rgba(255,255,255,0.12)] hover:bg-white/5 text-xs text-[#f2f2f0] font-medium transition-all active:scale-[0.98]"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to CleanIQ</span>
        </Link>
      </header>

      {/* Main Content */}
      <main className="max-w-3xl mx-auto px-6 py-16 space-y-8 flex-1">
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Alpha Privacy Guarantee</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            Privacy Policy
          </h1>
          <p className="text-sm text-[#8a8a86]">
            Last updated: September 2026 · CleanIQ v1.0-Alpha
          </p>
        </div>

        <div className="space-y-6 text-sm text-[#8a8a86] leading-relaxed">
          <section className="p-6 rounded-[14px] bg-white/[0.03] border border-[rgba(255,255,255,0.08)] space-y-3">
            <div className="flex items-center gap-2 text-white font-semibold">
              <Database className="w-4 h-4 text-[#ff6a3d]" />
              <h3>In-Memory Processing</h3>
            </div>
            <p>
              CleanIQ is an alpha research and data-quality inspection tool. When you upload a CSV or Excel dataset, your file is processed entirely in ephemeral server memory (RAM) utilizing Pandas data structures. We do not persist your raw datasets into permanent databases.
            </p>
          </section>

          <section className="p-6 rounded-[14px] bg-white/[0.03] border border-[rgba(255,255,255,0.08)] space-y-3">
            <div className="flex items-center gap-2 text-white font-semibold">
              <Clock className="w-4 h-4 text-[#ff6a3d]" />
              <h3>Automatic Session Cleanup (24h)</h3>
            </div>
            <p>
              Active dataset cleaning sessions and undo/redo operation histories are strictly transient. Sessions automatically expire and are purged from memory after 24 hours of inactivity by our automated background garbage collector.
            </p>
          </section>

          <section className="p-6 rounded-[14px] bg-white/[0.03] border border-[rgba(255,255,255,0.08)] space-y-3">
            <div className="flex items-center gap-2 text-white font-semibold">
              <Lock className="w-4 h-4 text-[#ff6a3d]" />
              <h3>Zero Third-Party Sharing</h3>
            </div>
            <p>
              Your uploaded records, column metadata, and cleaned exports are never sold, rented, monetized, or shared with third parties or advertising networks. Cleaning operations run strictly within your designated session boundary.
            </p>
          </section>

          <section className="p-6 rounded-[14px] bg-white/[0.03] border border-[rgba(255,255,255,0.08)] space-y-3">
            <h3 className="text-white font-semibold">Contact</h3>
            <p>
              If you have any questions or security feedback regarding this Alpha release, please contact the maintainer directly at{' '}
              <a
                href="mailto:ctabdulhadhi@gmail.com"
                className="text-[#ff6a3d] hover:underline font-medium"
              >
                ctabdulhadhi@gmail.com
              </a>.
            </p>
          </section>
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}

export default Privacy;
