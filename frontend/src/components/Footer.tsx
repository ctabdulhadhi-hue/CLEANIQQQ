import { Link } from 'react-router-dom';
import { Mail } from 'lucide-react';
import { LinkedinIcon, GithubIcon } from './icons/SocialIcons';

export const Footer = () => {
  return (
    <footer className="border-t border-[rgba(255,255,255,0.08)] bg-[#08080a] text-[#8a8a86] py-12 px-6">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center md:items-start justify-between gap-8">
        {/* Left column: Logo & Tagline */}
        <div className="space-y-3 text-center md:text-left max-w-sm">
          <Link
            to="/"
            className="inline-block transition-transform duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6a3d] rounded"
          >
            <img
              src="/logo-dark-bg.svg"
              alt="CleanIQ"
              className="h-8 w-auto object-contain mx-auto md:mx-0"
            />
          </Link>
          <p className="text-xs text-[#8a8a86] leading-relaxed">
            Intelligent, controlled data cleaning with zero silent mutations. Every fix previewed, auditable, and verified.
          </p>
        </div>

        {/* Right column: Navigation & Social Links */}
        <div className="flex flex-col sm:flex-row items-center md:items-end gap-6 sm:gap-10 text-xs">
          <div className="flex flex-wrap items-center justify-center gap-6 font-medium">
            <Link
              to="/privacy"
              className="text-[#93938e] hover:text-white transition-colors duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#ff6a3d] rounded px-1"
            >
              Privacy Policy
            </Link>
            <Link
              to="/terms"
              className="text-[#93938e] hover:text-white transition-colors duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#ff6a3d] rounded px-1"
            >
              Terms of Service
            </Link>
            <a
              href="mailto:ctabdulhadhi@gmail.com"
              className="text-[#93938e] hover:text-white inline-flex items-center gap-1.5 transition-colors duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#ff6a3d] rounded px-1"
            >
              <Mail className="w-3.5 h-3.5 text-[#ff6a3d]" />
              <span>Contact</span>
            </a>
          </div>

          {/* Social Icons */}
          <div className="flex items-center gap-2">
            <a
              href="https://www.linkedin.com/in/abdul-hadhi-707134382"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg text-[#93938e] hover:text-white hover:bg-white/5 transition-all duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6a3d]"
              aria-label="LinkedIn Profile"
              title="LinkedIn Profile"
            >
              <LinkedinIcon className="w-4 h-4" />
            </a>
            <a
              href="https://github.com/ctabdulhadhi"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg text-[#93938e] hover:text-white hover:bg-white/5 transition-all duration-150 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff6a3d]"
              aria-label="GitHub Repository"
              title="GitHub Profile"
            >
              <GithubIcon className="w-4 h-4" />
            </a>
          </div>
        </div>
      </div>

      {/* Bottom separator & Copyright */}
      <div className="max-w-7xl mx-auto mt-8 pt-6 border-t border-[rgba(255,255,255,0.06)] flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-[#71716b]">
        <p>© 2026 CleanIQ · V1.0-Alpha</p>
        <p className="flex items-center gap-2">
          <span>Self-contained in-memory sessions</span>
          <span>&bull;</span>
          <span>Open-source telemetry</span>
        </p>
      </div>
    </footer>
  );
};
