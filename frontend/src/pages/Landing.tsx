import { Suspense, lazy, useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Droplet,
  CopyCheck,
  Gauge,
  CheckCircle2,
  Menu,
  X,
  UploadCloud,
  AlertCircle,
  Download,
  Layers,
  Clock,
  Check,
} from 'lucide-react';
import Lenis from 'lenis';
import 'lenis/dist/lenis.css';
import { SplitText } from '../components/reactbits/SplitText';
import { TiltCard } from '../components/reactbits/TiltCard';
import { Preloader } from '../components/effects/Preloader';
import { MagneticButton } from '../components/effects/MagneticButton';
import { MarqueePartners } from '../components/effects/MarqueePartners';
import { useCountUp } from '../hooks/useCountUp';
import { useBackendStatus } from '../hooks/useBackendStatus';
import { loadSampleDataset } from '../services/api';
import { LinkedinIcon, GithubIcon } from '../components/icons/SocialIcons';
import { Footer } from '../components/Footer';

const DarkVeil = lazy(() => import('../components/effects/DarkVeil'));

export function Landing() {
  const location = useLocation();
  const navigate = useNavigate();
  const backend = useBackendStatus();

  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
    return false;
  });
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [loadingSample, setLoadingSample] = useState(false);

  const handleTrySample = async () => {
    if (!backend.isReady) return;
    try {
      setLoadingSample(true);
      const res = await loadSampleDataset();
      navigate(`/dataset?id=${encodeURIComponent(res.dataset_id)}`);
    } catch (err) {
      console.error('Failed to load sample dataset:', err);
      navigate('/dashboard');
    } finally {
      setLoadingSample(false);
    }
  };

  // Check prefers-reduced-motion
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  // Smooth scroll (Lenis) - Landing page only, destroyed on unmount
  useEffect(() => {
    if (prefersReducedMotion) return;

    const lenis = new Lenis({
      duration: 1.0,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      touchMultiplier: 1.5,
    });

    let rafId: number;
    function raf(time: number) {
      lenis.raf(time);
      rafId = requestAnimationFrame(raf);
    }
    rafId = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(rafId);
      lenis.destroy();
      document.documentElement.classList.remove('lenis', 'lenis-smooth', 'lenis-stopped');
      document.body.classList.remove('lenis', 'lenis-smooth', 'lenis-stopped');
    };
  }, [prefersReducedMotion]);

  // Lock body scroll when full-screen mobile menu is open
  useEffect(() => {
    if (isMobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobileMenuOpen]);

  // Scroll-triggered reveal for Quality Score Card
  const statCardRef = useRef<HTMLDivElement>(null);
  const [hasScrolledIntoView, setHasScrolledIntoView] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  useEffect(() => {
    if (hasScrolledIntoView || prefersReducedMotion) {
      return;
    }

    const card = statCardRef.current;
    if (!card) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setHasScrolledIntoView(true);
            observer.disconnect();
          }
        });
      },
      { threshold: 0.25 }
    );

    observer.observe(card);

    return () => {
      observer.disconnect();
    };
  }, [hasScrolledIntoView, prefersReducedMotion]);

  // Animated counters for the stat card
  const scoreCount = useCountUp(hasScrolledIntoView ? 94 : 0, { duration: 1100 });
  const completenessCount = useCountUp(hasScrolledIntoView ? 96 : 0, { duration: 1100 });
  const consistencyCount = useCountUp(hasScrolledIntoView ? 92 : 0, { duration: 1100 });
  const validityCount = useCountUp(hasScrolledIntoView ? 95 : 0, { duration: 1100 });
  const uniquenessCount = useCountUp(hasScrolledIntoView ? 93 : 0, { duration: 1100 });

  function handleLogoClick() {
    if (location.pathname === '/dashboard') {
      navigate('/');
    } else if (location.pathname !== '/') {
      navigate('/dashboard');
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  return (
    <div className="min-h-screen bg-[#0c0c0e] text-[#f2f2f0] font-sans selection:bg-[#ff6a3d]/30 selection:text-[#ffb08a]">
      {/* SECTION 0: BRANDED PRELOADER (First Visit Only) */}
      <Preloader />

      {/* SECTION 1: NAVBAR */}
      <header className="sticky top-0 z-50 bg-[#0c0c0e]/80 backdrop-blur-md border-b border-[rgba(255,255,255,0.08)]">
        <div className="max-w-7xl mx-auto px-6 h-18 flex items-center justify-between">
          {/* Logo / Wordmark */}
          <button
            type="button"
            id="landing-navbar-logo-btn"
            onClick={handleLogoClick}
            className="flex items-center cursor-pointer group hover:opacity-90 hover:brightness-105 transition-all duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6a3d] bg-transparent border-none p-0 text-left rounded"
            aria-label="CleanIQ Logo"
          >
            <img
              src="/logo-dark-bg.svg"
              alt="CleanIQ"
              className="h-8 w-auto object-contain transition-transform duration-150 group-hover:scale-[1.02]"
            />
          </button>

          {/* Centered Nav Links: Product · Features · Roadmap · Docs */}
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-[#93938e]">
            <a
              href="#product"
              className="hover:text-white transition-colors duration-150 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#ff6a3d] rounded px-1"
            >
              Product
            </a>
            <a
              href="#features"
              className="hover:text-white transition-colors duration-150 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#ff6a3d] rounded px-1"
            >
              Features
            </a>
            <a
              href="#roadmap"
              className="hover:text-white transition-colors duration-150 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#ff6a3d] rounded px-1"
            >
              Roadmap
            </a>
            <a
              href="https://github.com/ctabdulhadhi-hue/cleaniq#readme"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white transition-colors duration-150 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#ff6a3d] rounded px-1"
            >
              Docs
            </a>
          </nav>

          {/* Right Action Icons & Status Pill (Desktop) & Hamburger Menu (Mobile) */}
          <div className="flex items-center gap-3">
            {/* Backend Status Indicator Pill (Reserved width to prevent layout shift) */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-[rgba(255,255,255,0.08)] text-xs min-h-[32px]">
              <span
                className={`w-2 h-2 rounded-full ${
                  backend.isOnline
                    ? 'bg-emerald-400 status-dot-pulse'
                    : backend.isOffline
                    ? 'bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.8)]'
                    : 'bg-amber-400 animate-pulse'
                }`}
              />
              <span className="text-[#f2f2f0] text-[11px] font-medium">
                {backend.isOnline
                  ? 'Backend Online'
                  : backend.isOffline
                  ? 'Backend Unavailable'
                  : 'Checking backend...'}
              </span>
              {backend.isOffline && (
                <button
                  onClick={backend.checkStatus}
                  className="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 border border-rose-500/30 font-semibold active:scale-[0.98] transition-all"
                  title="Retry Connection"
                >
                  Retry Connection
                </button>
              )}
            </div>

            {/* Social Icons Group (Desktop): LinkedIn immediately left of GitHub */}
            <div className="hidden sm:flex items-center gap-1">
              <a
                href="https://www.linkedin.com/in/abdul-hadhi-707134382"
                target="_blank"
                rel="noopener noreferrer"
                id="navbar-linkedin-link"
                className="p-2 rounded-lg text-[#93938e] hover:text-white hover:bg-white/5 transition-all duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6a3d]"
                aria-label="LinkedIn"
                title="LinkedIn Profile"
              >
                <LinkedinIcon className="w-4 h-4" />
              </a>
              <a
                href="https://github.com/ctabdulhadhi"
                target="_blank"
                rel="noopener noreferrer"
                id="navbar-github-link"
                className="p-2 rounded-lg text-[#93938e] hover:text-white hover:bg-white/5 transition-all duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6a3d]"
                aria-label="GitHub"
                title="GitHub"
              >
                <GithubIcon className="w-4 h-4" />
              </a>
            </div>

            {/* Hamburger Button (Mobile) */}
            <button
              type="button"
              id="mobile-menu-toggle-btn"
              onClick={() => setIsMobileMenuOpen((prev) => !prev)}
              className="md:hidden p-2 rounded-lg text-[#93938e] hover:text-white hover:bg-white/5 transition-colors active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6a3d]"
              aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
            >
              {isMobileMenuOpen ? <X className="w-6 h-6 text-white" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </header>

      {/* FULL-SCREEN MOBILE MENU OVERLAY */}
      <div
        id="fullscreen-mobile-menu"
        className={`fixed inset-0 z-50 bg-[#0c0c0e]/98 backdrop-blur-2xl flex flex-col justify-between p-8 md:hidden transition-all duration-300 ease-in-out ${
          isMobileMenuOpen
            ? 'opacity-100 pointer-events-auto translate-y-0'
            : 'opacity-0 pointer-events-none -translate-y-3'
        }`}
        aria-hidden={!isMobileMenuOpen}
      >
        <div className="flex items-center justify-between">
          <img src="/logo-dark-bg.svg" alt="CleanIQ" className="h-8 w-auto object-contain" />
          <button
            type="button"
            id="mobile-menu-close-btn"
            onClick={() => setIsMobileMenuOpen(false)}
            className="p-2.5 rounded-full bg-white/5 border border-white/10 text-white hover:bg-white/10 transition-colors active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6a3d]"
            aria-label="Close menu"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Backend Status in Mobile Menu */}
        <div className="p-3 rounded-xl bg-white/[0.03] border border-[rgba(255,255,255,0.08)] flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                backend.isOnline
                  ? 'bg-emerald-400 status-dot-pulse'
                  : backend.isOffline
                  ? 'bg-rose-400'
                  : 'bg-amber-400 animate-pulse'
              }`}
            />
            <span className="text-[#f2f2f0]">
              {backend.isOnline
                ? 'Backend Online'
                : backend.isOffline
                ? 'Backend Unavailable'
                : 'Checking backend...'}
            </span>
          </div>
          {backend.isOffline && (
            <button
              onClick={backend.checkStatus}
              className="text-[11px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-semibold"
              title="Retry Connection"
            >
              Retry Connection
            </button>
          )}
        </div>

        <nav className="flex flex-col gap-6 my-auto text-left">
          <a
            href="#product"
            onClick={() => setIsMobileMenuOpen(false)}
            className="text-3xl font-bold tracking-tight text-white/90 hover:text-[#ff6a3d] transition-colors"
          >
            Product
          </a>
          <a
            href="#features"
            onClick={() => setIsMobileMenuOpen(false)}
            className="text-3xl font-bold tracking-tight text-white/90 hover:text-[#ff6a3d] transition-colors"
          >
            Features
          </a>
          <a
            href="#roadmap"
            onClick={() => setIsMobileMenuOpen(false)}
            className="text-3xl font-bold tracking-tight text-white/90 hover:text-[#ff6a3d] transition-colors"
          >
            Roadmap
          </a>
          <a
            href="https://github.com/ctabdulhadhi-hue/cleaniq#readme"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setIsMobileMenuOpen(false)}
            className="text-3xl font-bold tracking-tight text-white/90 hover:text-[#ff6a3d] transition-colors"
          >
            Docs
          </a>
        </nav>

        <div className="pt-6 border-t border-white/10 flex flex-col gap-4">
          <Link
            to="/dashboard"
            onClick={() => setIsMobileMenuOpen(false)}
            className="w-full text-center py-4 rounded-xl bg-[#ff6a3d] hover:bg-[#ff7b50] text-[#0c0c0e] font-bold text-base transition-colors active:scale-[0.98]"
          >
            Launch Dashboard
          </Link>
          {/* Social Icons row at the bottom of mobile menu */}
          <div className="flex items-center justify-center gap-3 py-1">
            <a
              href="https://www.linkedin.com/in/abdul-hadhi-707134382"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2.5 rounded-full bg-white/5 border border-white/10 text-[#93938e] hover:text-white hover:bg-white/10 transition-colors flex items-center justify-center active:scale-[0.98]"
              aria-label="LinkedIn Profile"
              title="LinkedIn Profile"
            >
              <LinkedinIcon className="w-5 h-5" />
            </a>
            <a
              href="https://github.com/ctabdulhadhi"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2.5 rounded-full bg-white/5 border border-white/10 text-[#93938e] hover:text-white hover:bg-white/10 transition-colors flex items-center justify-center active:scale-[0.98]"
              aria-label="GitHub Profile"
              title="GitHub Profile"
            >
              <GithubIcon className="w-5 h-5" />
            </a>
          </div>
        </div>
      </div>

      {/* SECTION 2: HERO SECTION WITH DARK VEIL SHADER */}
      <section className="relative min-h-[82vh] flex items-center justify-center text-center px-6 overflow-hidden">
        {/* DarkVeil Shader Background (WebGL Canvas) & Tint Layer */}
        {!prefersReducedMotion ? (
          <>
            <div className="absolute inset-0 z-0 pointer-events-none opacity-80 mix-blend-screen">
              <Suspense fallback={<div className="w-full h-full bg-[#0c0c0e]" />}>
                <DarkVeil
                  hueShift={208}
                  noiseIntensity={0.03}
                  speed={0.35}
                  scanlineIntensity={0.05}
                  scanlineFrequency={0.0}
                  warpAmount={0.08}
                />
              </Suspense>
            </div>

            {/* Deterministic orange tint layer directly above canvas (mix-blend-mode: color keeps brightness pattern but replaces hue with orange) */}
            <div
              className="absolute inset-0 pointer-events-none z-[1]"
              style={{
                backgroundColor: '#ff6a3d',
                mixBlendMode: 'color',
                opacity: 0.7,
              }}
            />
          </>
        ) : (
          <div className="absolute inset-0 z-0 pointer-events-none bg-[#0c0c0e]" />
        )}

        {/* Radial dark vignette overlay to keep generative glow centered behind hero headline */}
        <div
          className="absolute inset-0 z-[2] pointer-events-none"
          style={{
            background: 'radial-gradient(ellipse at 50% 30%, transparent 0%, #0c0c0e 75%)',
          }}
        />

        {/* Dark bottom fade overlay for legibility and seamless page fade */}
        <div
          className="absolute inset-0 z-[2] pointer-events-none"
          style={{
            background:
              'linear-gradient(to bottom, rgba(12, 12, 14, 0.25) 0%, rgba(12, 12, 14, 0.65) 60%, #0c0c0e 100%)',
          }}
        />

        <div className="relative z-10 max-w-4xl mx-auto pt-16 pb-20">
          {/* Eyebrow badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/5 border border-[rgba(255,255,255,0.1)] text-[#f2f2f0] text-xs font-semibold mb-8 backdrop-blur-sm">
            <Sparkles className="w-3.5 h-3.5 text-[#ff6a3d]" />
            <span>Audit-ready data cleaning with zero silent mutations</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-white mb-6 leading-[1.08]">
            <SplitText
              text="Dirty data in,"
              className="justify-center"
              splitType="words"
              delay={35}
              duration={0.6}
            />
            <SplitText
              text="clean decisions"
              className="text-[#ff6a3d] justify-center"
              splitType="words"
              delay={45}
              duration={0.6}
            />
          </h1>

          <p className="text-base md:text-lg text-[#93938e] max-w-2xl mx-auto leading-relaxed mb-10">
            Automate missing value imputation, duplicate detection, and transparent quality scoring in seconds.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 relative z-20">
            {/* Magnetic primary CTA on desktop */}
            <MagneticButton>
              <Link
                to="/dashboard"
                id="try-cleaniq-btn"
                className="w-full sm:w-auto inline-flex items-center justify-center bg-[#ff6a3d] hover:bg-[#ff7b50] text-[#0c0c0e] font-semibold px-7 py-3.5 rounded-xl transition-all cursor-pointer text-sm active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6a3d]"
              >
                Try CleanIQ
              </Link>
            </MagneticButton>

            {/* Try with sample data Button */}
            <button
              type="button"
              id="try-sample-btn"
              onClick={handleTrySample}
              disabled={loadingSample || !backend.isOnline}
              title={
                !backend.isOnline
                  ? backend.isOffline
                    ? "Backend Unavailable — CleanIQ's processing server is temporarily unavailable"
                    : 'Checking backend...'
                  : 'Load demo sales dataset'
              }
              className={`w-full sm:w-auto inline-flex items-center justify-center gap-2 border font-medium px-7 py-3.5 rounded-xl transition-all text-sm active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6a3d] ${
                !backend.isOnline
                  ? 'border-[rgba(255,255,255,0.08)] bg-white/[0.02] text-[#8a8a86] cursor-not-allowed opacity-60'
                  : 'border-[rgba(255,255,255,0.15)] hover:bg-white/5 text-slate-200 cursor-pointer'
              }`}
            >
              {loadingSample ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  <span>Loading sample...</span>
                </>
              ) : (
                <>
                  <span>Try with sample data</span>
                  {!backend.isOnline && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-[#8a8a86]">
                      {backend.isOffline ? 'Offline' : 'Checking...'}
                    </span>
                  )}
                </>
              )}
            </button>
          </div>

          {/* Backend offline/checking status banner (Min-height reserved to prevent layout shift) */}
          <div className="min-h-[48px] mt-6 flex items-center justify-center">
            {backend.isOffline ? (
              <div
                id="landing-backend-offline-banner"
                className="inline-flex flex-col sm:flex-row items-center gap-2.5 px-4 py-2 rounded-xl text-xs font-medium border bg-rose-500/10 border-rose-500/30 text-rose-300 shadow-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.8)] shrink-0" />
                  <span>Backend Unavailable — CleanIQ's processing server is temporarily unavailable</span>
                </div>
                <button
                  onClick={backend.checkStatus}
                  className="sm:ml-2 text-[11px] px-2.5 py-1 rounded-md bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-white font-semibold transition-all active:scale-[0.98]"
                >
                  Retry Connection
                </button>
              </div>
            ) : backend.isChecking ? (
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium bg-white/[0.03] border border-white/[0.08] text-[#8a8a86]">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                <span>Checking backend...</span>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      {/* SECTION 3: INFINITELY SCROLLING HORIZONTAL MARQUEE TECH-PARTNER STRIP */}
      <MarqueePartners />

      {/* SECTION 4: PRODUCT PROOF SECTION (#product) */}
      <section id="product" className="py-24 px-6 md:px-12 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left Column */}
          <div>
            <span className="text-xs font-semibold text-[#ff6a3d] tracking-wider uppercase mb-3 block">
              Auditable & Transparent
            </span>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-white mb-5 leading-tight">
              Confidence in every dataset
            </h2>
            <p className="text-sm md:text-base text-[#8a8a86] leading-relaxed mb-8">
              CleanIQ keeps your team in control. Preview every transformation, track full step histories, and export comprehensive quality reports.
            </p>
            <ul className="space-y-4 text-sm font-medium text-slate-200">
              <li className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-[#ff6a3d] shrink-0" />
                <span>Full operation history with undo/redo</span>
              </li>
              <li className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-[#ff6a3d] shrink-0" />
                <span>Order ID integrity & transaction conflict detection</span>
              </li>
              <li className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-[#ff6a3d] shrink-0" />
                <span>Exportable executive PDF & HTML quality reports</span>
              </li>
            </ul>
          </div>

          {/* Right Column: Dark Stat Card with Scroll-Triggered Reveal & Spotlight */}
          <div ref={statCardRef}>
            <TiltCard
              tiltAmplitude={5}
              spotlightColor="rgba(255, 106, 61, 0.14)"
              className="bg-[#131317] border border-[rgba(255,255,255,0.08)] rounded-[14px] p-8 md:p-10 shadow-lg hover:border-[rgba(255,255,255,0.15)]"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-[#8a8a86] uppercase tracking-wider">
                  Overall Dataset Health
                </span>
                <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  ▲ 12% Improved
                </span>
              </div>

              <div className="flex items-baseline gap-2 mb-8">
                <span className="text-5xl md:text-6xl font-extrabold text-white tracking-tight">
                  {scoreCount}
                </span>
                <span className="text-2xl font-bold text-[#71716b]">/ 100</span>
              </div>

              {/* 4-Bar Quality Breakdown Chart with Scroll-Triggered Growth */}
              <div className="space-y-4 pt-4 border-t border-[rgba(255,255,255,0.08)]">
                <p className="text-xs font-medium text-[#71716b] uppercase tracking-wider mb-3">
                  Dimension Breakdown
                </p>

                {/* Completeness Bar */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-slate-300">Completeness</span>
                    <span className="text-[#ff6a3d]">{completenessCount}%</span>
                  </div>
                  <div className="h-2.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#ff6a3d] rounded-full"
                      style={{
                        width: hasScrolledIntoView ? '96%' : '0%',
                        transition: prefersReducedMotion
                          ? 'none'
                          : 'width 1.1s cubic-bezier(0.16, 1, 0.3, 1)',
                      }}
                    />
                  </div>
                </div>

                {/* Consistency Bar */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-slate-300">Consistency</span>
                    <span className="text-slate-400">{consistencyCount}%</span>
                  </div>
                  <div className="h-2.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-slate-400/80 rounded-full"
                      style={{
                        width: hasScrolledIntoView ? '92%' : '0%',
                        transition: prefersReducedMotion
                          ? 'none'
                          : 'width 1.1s cubic-bezier(0.16, 1, 0.3, 1)',
                      }}
                    />
                  </div>
                </div>

                {/* Validity Bar */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-slate-300">Validity</span>
                    <span className="text-slate-400">{validityCount}%</span>
                  </div>
                  <div className="h-2.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-slate-400/80 rounded-full"
                      style={{
                        width: hasScrolledIntoView ? '95%' : '0%',
                        transition: prefersReducedMotion
                          ? 'none'
                          : 'width 1.1s cubic-bezier(0.16, 1, 0.3, 1)',
                      }}
                    />
                  </div>
                </div>

                {/* Uniqueness Bar */}
                <div>
                  <div className="flex justify-between text-xs font-medium mb-1.5">
                    <span className="text-slate-300">Uniqueness</span>
                    <span className="text-slate-400">{uniquenessCount}%</span>
                  </div>
                  <div className="h-2.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-slate-400/80 rounded-full"
                      style={{
                        width: hasScrolledIntoView ? '93%' : '0%',
                        transition: prefersReducedMotion
                          ? 'none'
                          : 'width 1.1s cubic-bezier(0.16, 1, 0.3, 1)',
                      }}
                    />
                  </div>
                </div>
              </div>
            </TiltCard>
          </div>
        </div>
      </section>

      {/* SECTION 5: 3-CARD FEATURE SECTION (#features) */}
      <section id="features" className="py-24 px-6 md:px-12 max-w-7xl mx-auto border-t border-[rgba(255,255,255,0.06)]">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="text-xs font-semibold text-[#ff6a3d] tracking-wider uppercase mb-3 block">
            Powerful Cleaning Engine
          </span>
          <h2 className="text-2xl md:text-4xl font-bold tracking-tight text-white mb-4">
            Everything your dataset needs, in one pass
          </h2>
          <p className="text-sm md:text-base text-[#8a8a86]">
            Inspect, clean, and validate complex tabular datasets with full step auditability.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Missing Values */}
          <TiltCard
            delay={0}
            tiltAmplitude={6}
            spotlightColor="rgba(255, 106, 61, 0.12)"
            className="bg-[#131317] border border-[rgba(255,255,255,0.08)] rounded-[14px] p-7 flex flex-col justify-between hover:border-[rgba(255,255,255,0.15)]"
          >
            <div>
              <div className="w-11 h-11 rounded-xl bg-[#ff6a3d]/10 border border-[#ff6a3d]/20 flex items-center justify-center mb-6">
                <Droplet className="w-5.5 h-5.5 text-[#ff6a3d]" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Missing Values</h3>
              <p className="text-sm text-[#8a8a86] leading-relaxed">
                Preview smart fills, custom value substitutions, and statistical imputations across affected columns before applying changes.
              </p>
            </div>
          </TiltCard>

          {/* Card 2: Duplicate & Conflict Detection */}
          <TiltCard
            delay={0.1}
            tiltAmplitude={6}
            spotlightColor="rgba(255, 106, 61, 0.12)"
            className="bg-[#131317] border border-[rgba(255,255,255,0.08)] rounded-[14px] p-7 flex flex-col justify-between hover:border-[rgba(255,255,255,0.15)]"
          >
            <div>
              <div className="w-11 h-11 rounded-xl bg-[#ff6a3d]/10 border border-[#ff6a3d]/20 flex items-center justify-center mb-6">
                <CopyCheck className="w-5.5 h-5.5 text-[#ff6a3d]" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Duplicate & Conflict Detection</h3>
              <p className="text-sm text-[#8a8a86] leading-relaxed">
                Intelligently distinguish between valid order-line items and actual Order ID transaction conflicts.
              </p>
            </div>
          </TiltCard>

          {/* Card 3: Quality Scoring */}
          <TiltCard
            delay={0.2}
            tiltAmplitude={6}
            spotlightColor="rgba(255, 106, 61, 0.12)"
            className="bg-[#131317] border border-[rgba(255,255,255,0.08)] rounded-[14px] p-7 flex flex-col justify-between hover:border-[rgba(255,255,255,0.15)]"
          >
            <div>
              <div className="w-11 h-11 rounded-xl bg-[#ff6a3d]/10 border border-[#ff6a3d]/20 flex items-center justify-center mb-6">
                <Gauge className="w-5.5 h-5.5 text-[#ff6a3d]" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Quality Scoring</h3>
              <p className="text-sm text-[#8a8a86] leading-relaxed">
                A transparent 16-point score built from completeness, consistency, validity, and uniqueness dimensions.
              </p>
            </div>
          </TiltCard>
        </div>
      </section>

      {/* SECTION 6: HOW IT WORKS (#how-it-works) */}
      <section id="how-it-works" className="py-24 px-6 md:px-12 max-w-7xl mx-auto border-t border-[rgba(255,255,255,0.06)]">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="text-xs font-semibold text-[#ff6a3d] tracking-wider uppercase mb-3 block">
            Controlled Workflow
          </span>
          <h2 className="text-2xl md:text-4xl font-bold tracking-tight text-white mb-4">
            How CleanIQ works
          </h2>
          <p className="text-sm md:text-base text-[#8a8a86]">
            Four simple steps from messy raw data to auditable, production-ready tables.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Step 1: Upload */}
          <TiltCard
            tiltAmplitude={5}
            spotlightColor="rgba(255, 106, 61, 0.12)"
            className="bg-[#131317] border border-[rgba(255,255,255,0.08)] rounded-[14px] p-6 flex flex-col justify-between hover:border-[rgba(255,255,255,0.15)]"
          >
            <div>
              <div className="flex items-center justify-between mb-5">
                <div className="w-10 h-10 rounded-xl bg-[#ff6a3d]/10 border border-[#ff6a3d]/20 flex items-center justify-center text-[#ff6a3d]">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <span className="text-xs font-mono font-bold text-[#8a8a86] px-2 py-0.5 rounded bg-white/5">
                  01
                </span>
              </div>
              <h3 className="text-base font-semibold text-white mb-2">Upload</h3>
              <p className="text-xs text-[#8a8a86] leading-relaxed">
                Drop in your raw CSV or Excel dataset. All processing runs in ephemeral in-memory sessions without permanent storage.
              </p>
            </div>
          </TiltCard>

          {/* Step 2: Review detected issues */}
          <TiltCard
            tiltAmplitude={5}
            spotlightColor="rgba(255, 106, 61, 0.12)"
            className="bg-[#131317] border border-[rgba(255,255,255,0.08)] rounded-[14px] p-6 flex flex-col justify-between hover:border-[rgba(255,255,255,0.15)]"
          >
            <div>
              <div className="flex items-center justify-between mb-5">
                <div className="w-10 h-10 rounded-xl bg-[#ff6a3d]/10 border border-[#ff6a3d]/20 flex items-center justify-center text-[#ff6a3d]">
                  <AlertCircle className="w-5 h-5" />
                </div>
                <span className="text-xs font-mono font-bold text-[#8a8a86] px-2 py-0.5 rounded bg-white/5">
                  02
                </span>
              </div>
              <h3 className="text-base font-semibold text-white mb-2">Review detected issues</h3>
              <p className="text-xs text-[#8a8a86] leading-relaxed">
                Automated 16-point audit scans missing cells, exact and fuzzy duplicates, invalid dates, and Order ID transaction conflicts.
              </p>
            </div>
          </TiltCard>

          {/* Step 3: Approve each fix */}
          <TiltCard
            tiltAmplitude={5}
            spotlightColor="rgba(255, 106, 61, 0.12)"
            className="bg-[#131317] border border-[rgba(255,255,255,0.08)] rounded-[14px] p-6 flex flex-col justify-between hover:border-[rgba(255,255,255,0.15)]"
          >
            <div>
              <div className="flex items-center justify-between mb-5">
                <div className="w-10 h-10 rounded-xl bg-[#ff6a3d]/10 border border-[#ff6a3d]/20 flex items-center justify-center text-[#ff6a3d]">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <span className="text-xs font-mono font-bold text-[#8a8a86] px-2 py-0.5 rounded bg-white/5">
                  03
                </span>
              </div>
              <h3 className="text-base font-semibold text-white mb-2">Approve each fix</h3>
              <p className="text-xs text-[#8a8a86] leading-relaxed">
                Zero silent mutations. Preview interactive before/after diffs for every imputation, trim, or ID re-indexing before committing.
              </p>
            </div>
          </TiltCard>

          {/* Step 4: Export cleaned data + report */}
          <TiltCard
            tiltAmplitude={5}
            spotlightColor="rgba(255, 106, 61, 0.12)"
            className="bg-[#131317] border border-[rgba(255,255,255,0.08)] rounded-[14px] p-6 flex flex-col justify-between hover:border-[rgba(255,255,255,0.15)]"
          >
            <div>
              <div className="flex items-center justify-between mb-5">
                <div className="w-10 h-10 rounded-xl bg-[#ff6a3d]/10 border border-[#ff6a3d]/20 flex items-center justify-center text-[#ff6a3d]">
                  <Download className="w-5 h-5" />
                </div>
                <span className="text-xs font-mono font-bold text-[#8a8a86] px-2 py-0.5 rounded bg-white/5">
                  04
                </span>
              </div>
              <h3 className="text-base font-semibold text-white mb-2">Export data + report</h3>
              <p className="text-xs text-[#8a8a86] leading-relaxed">
                Download verified cleaned CSV/XLSX files accompanied by executive-ready Before vs. After audit reports in PDF and HTML formats.
              </p>
            </div>
          </TiltCard>
        </div>
      </section>

      {/* SECTION 7: ROADMAP (#roadmap) */}
      <section id="roadmap" className="py-24 px-6 md:px-12 max-w-7xl mx-auto border-t border-[rgba(255,255,255,0.06)]">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="text-xs font-semibold text-[#ff6a3d] tracking-wider uppercase mb-3 block">
            Product Evolution
          </span>
          <h2 className="text-2xl md:text-4xl font-bold tracking-tight text-white mb-4">
            CleanIQ Roadmap
          </h2>
          <p className="text-sm md:text-base text-[#8a8a86]">
            Continuous engineering toward enterprise-grade, transparent data quality.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Phase 1: Current */}
          <TiltCard
            tiltAmplitude={5}
            spotlightColor="rgba(52, 211, 153, 0.12)"
            className="bg-[#131317] border border-emerald-500/25 rounded-[14px] p-7 flex flex-col justify-between space-y-4"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold font-mono uppercase tracking-wider text-emerald-400">
                  Phase 1 · Available
                </span>
                <span className="px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-[10px] font-semibold">
                  v1.0-Alpha
                </span>
              </div>
              <h3 className="text-lg font-bold text-white">Controlled Cleaning Core</h3>
              <ul className="space-y-2.5 text-xs text-[#8a8a86]">
                <li className="flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                  <span>Zero silent mutations with interactive diff preview</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                  <span>Order ID transaction conflict analysis & resolution</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                  <span>16-point automated data quality audit engine</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                  <span>Full undo/redo session replay & exportable PDF/HTML reports</span>
                </li>
              </ul>
            </div>
          </TiltCard>

          {/* Phase 2: Upcoming */}
          <TiltCard
            tiltAmplitude={5}
            spotlightColor="rgba(251, 191, 36, 0.12)"
            className="bg-[#131317] border border-amber-500/20 rounded-[14px] p-7 flex flex-col justify-between space-y-4"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold font-mono uppercase tracking-wider text-amber-400">
                  Phase 2 · In Progress
                </span>
                <span className="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 text-[10px] font-semibold">
                  v1.1
                </span>
              </div>
              <h3 className="text-lg font-bold text-white">Fuzzy Matching & Custom Rules</h3>
              <ul className="space-y-2.5 text-xs text-[#8a8a86]">
                <li className="flex items-start gap-2">
                  <Clock className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                  <span>Multi-dataset fuzzy matching and cross-table joins</span>
                </li>
                <li className="flex items-start gap-2">
                  <Clock className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                  <span>Machine-learning duplicate clustering & phonetic algorithms</span>
                </li>
                <li className="flex items-start gap-2">
                  <Clock className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                  <span>Interactive business rule & schema constraint builder</span>
                </li>
                <li className="flex items-start gap-2">
                  <Clock className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                  <span>Automated outlier treatment recommendations</span>
                </li>
              </ul>
            </div>
          </TiltCard>

          {/* Phase 3: Planned */}
          <TiltCard
            tiltAmplitude={5}
            spotlightColor="rgba(255, 106, 61, 0.12)"
            className="bg-[#131317] border border-[rgba(255,255,255,0.08)] rounded-[14px] p-7 flex flex-col justify-between space-y-4"
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold font-mono uppercase tracking-wider text-[#ff6a3d]">
                  Phase 3 · Planned
                </span>
                <span className="px-2 py-0.5 rounded-full bg-[#ff6a3d]/15 text-[#ffb08a] border border-[#ff6a3d]/30 text-[10px] font-semibold">
                  v2.0
                </span>
              </div>
              <h3 className="text-lg font-bold text-white">Warehouse & Pipeline CI/CD</h3>
              <ul className="space-y-2.5 text-xs text-[#8a8a86]">
                <li className="flex items-start gap-2">
                  <Layers className="w-3.5 h-3.5 text-[#ff6a3d] mt-0.5 shrink-0" />
                  <span>Native connectors for Snowflake, BigQuery & PostgreSQL</span>
                </li>
                <li className="flex items-start gap-2">
                  <Layers className="w-3.5 h-3.5 text-[#ff6a3d] mt-0.5 shrink-0" />
                  <span>Automated CI/CD quality gate check on data ingestion</span>
                </li>
                <li className="flex items-start gap-2">
                  <Layers className="w-3.5 h-3.5 text-[#ff6a3d] mt-0.5 shrink-0" />
                  <span>Continuous anomaly detection & alert webhooks</span>
                </li>
                <li className="flex items-start gap-2">
                  <Layers className="w-3.5 h-3.5 text-[#ff6a3d] mt-0.5 shrink-0" />
                  <span>Team workspaces with audit permission controls</span>
                </li>
              </ul>
            </div>
          </TiltCard>
        </div>
      </section>

      {/* SECTION 8: FOOTER */}
      <Footer />
    </div>
  );
}

export default Landing;
