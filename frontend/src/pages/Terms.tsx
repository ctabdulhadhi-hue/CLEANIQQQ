import { Link } from 'react-router-dom';
import { ArrowLeft, FileText, CheckCircle2, AlertTriangle, Scale } from 'lucide-react';
import { Footer } from '../components/Footer';

export function Terms() {
  return (
    <div className="min-h-screen bg-[#0c0c0e] text-[#f2f2f0] flex flex-col justify-between">
      {/* Top Navigation */}
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
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#ff6a3d]/10 border border-[#ff6a3d]/25 text-[#ffb08a] text-xs font-semibold">
            <FileText className="w-3.5 h-3.5 text-[#ff6a3d]" />
            <span>Usage & Integrity Agreement</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            Terms of Service
          </h1>
          <p className="text-sm text-[#8a8a86]">
            Last updated: September 2026 · CleanIQ v1.0-Alpha
          </p>
        </div>

        <div className="space-y-6 text-sm text-[#8a8a86] leading-relaxed">
          <section className="p-6 rounded-[14px] bg-white/[0.03] border border-[rgba(255,255,255,0.08)] space-y-3">
            <div className="flex items-center gap-2 text-white font-semibold">
              <Scale className="w-4 h-4 text-[#ff6a3d]" />
              <h3>Alpha Service Provision ("As-Is")</h3>
            </div>
            <p>
              CleanIQ is currently released as a v1.0-Alpha service. It is provided on an "as is" and "as available" basis without warranties of any kind. While our core principle is "zero silent mutations" with interactive previews, users are encouraged to verify exported datasets prior to downstream production pipeline integration.
            </p>
          </section>

          <section className="p-6 rounded-[14px] bg-white/[0.03] border border-[rgba(255,255,255,0.08)] space-y-3">
            <div className="flex items-center gap-2 text-white font-semibold">
              <CheckCircle2 className="w-4 h-4 text-[#ff6a3d]" />
              <h3>User Responsibilities & Data Control</h3>
            </div>
            <p>
              You maintain full ownership of all datasets, columns, and data transformations executed in CleanIQ. You are solely responsible for ensuring you possess appropriate rights and authorization to upload and analyze your data.
            </p>
          </section>

          <section className="p-6 rounded-[14px] bg-white/[0.03] border border-[rgba(255,255,255,0.08)] space-y-3">
            <div className="flex items-center gap-2 text-white font-semibold">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h3>Ephemeral Storage Limitation</h3>
            </div>
            <p>
              CleanIQ does not serve as a permanent file hosting or backup service. Memory sessions expire after 24 hours of inactivity. Please always export and download your cleaned datasets and audit reports upon concluding your session.
            </p>
          </section>

          <section className="p-6 rounded-[14px] bg-white/[0.03] border border-[rgba(255,255,255,0.08)] space-y-3">
            <h3 className="text-white font-semibold">Governing Law & Inquiries</h3>
            <p>
              Questions or notifications regarding these Terms should be submitted directly via email to{' '}
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

export default Terms;
