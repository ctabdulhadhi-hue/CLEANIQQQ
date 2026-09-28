import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Award,
  AlertCircle,
} from 'lucide-react';
import type { QualitySummary } from '../services/api';

interface DataQualitySummaryCardProps {
  summary: QualitySummary | null | undefined;
  filename?: string;
  className?: string;
}

export const DataQualitySummaryCard = ({
  summary,
  filename,
  className = '',
}: DataQualitySummaryCardProps) => {
  if (!summary) return null;

  const scorePct = Number((summary.overall_score * 100).toFixed(1));

  const getStatusBadge = (status: 'clean' | 'warning' | 'error') => {
    switch (status) {
      case 'clean':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>✓ Clean</span>
          </span>
        );
      case 'warning':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>⚠ Warning</span>
          </span>
        );
      case 'error':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" />
            <span>✕ Error</span>
          </span>
        );
    }
  };

  const getCardBorder = (status: 'clean' | 'warning' | 'error') => {
    switch (status) {
      case 'clean':
        return 'border-[rgba(255,255,255,0.08)] hover:border-emerald-500/30';
      case 'warning':
        return 'border-amber-500/25 bg-amber-500/[0.02]';
      case 'error':
        return 'border-rose-500/30 bg-rose-500/[0.02]';
    }
  };

  return (
    <div className={`rounded-[16px] bg-white/[0.03] border border-[rgba(255,255,255,0.08)] p-6 space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[rgba(255,255,255,0.08)]">
        <div>
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-[#ff6a3d]" />
            <h3 className="text-base font-bold text-white tracking-tight">
              Data Quality Summary
            </h3>
            {getStatusBadge(summary.overall_status)}
          </div>
          {filename && (
            <p className="text-xs text-[#8a8a86] mt-1">
              Evaluated on dataset: <strong className="text-white">{filename}</strong>
            </p>
          )}
        </div>

        {/* Overall Quality Score Meter */}
        <div className="flex items-center gap-4 bg-white/[0.02] px-4 py-2 rounded-xl border border-[rgba(255,255,255,0.06)]">
          <div className="text-right">
            <div className="text-[11px] uppercase tracking-wider text-[#8a8a86] font-semibold">
              Overall Quality Score
            </div>
            <div className="text-2xl font-black font-mono text-[#ff6a3d]">
              {scorePct}%
            </div>
          </div>
          <div className="w-10 h-10 rounded-full border-2 border-[#ff6a3d]/30 flex items-center justify-center bg-[#ff6a3d]/10">
            <Award className="w-5 h-5 text-[#ff6a3d]" />
          </div>
        </div>
      </div>

      {/* 8 Primary Dimension Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {summary.metrics.map((metric, idx) => (
          <div
            key={idx}
            className={`p-3.5 rounded-xl bg-white/[0.02] border transition-all ${getCardBorder(
              metric.status
            )}`}
          >
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span className="text-xs text-[#8a8a86] font-medium truncate" title={metric.name}>
                {metric.name}
              </span>
              {getStatusBadge(metric.status)}
            </div>
            <div className="text-xl font-bold font-mono text-white">
              {metric.count.toLocaleString()}
            </div>
            <div className="text-[11px] text-[#8a8a86] mt-1 truncate" title={metric.detail}>
              {metric.detail}
            </div>
          </div>
        ))}
      </div>

      {/* Detected Quality Dimensions & Issues */}
      {summary.issues && summary.issues.length > 0 && (
        <div className="space-y-2 pt-2">
          <div className="text-xs font-semibold uppercase tracking-wider text-[#8a8a86] flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            <span>Detailed Quality Findings ({summary.issues.length})</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {summary.issues.slice(0, 6).map((issue, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-white/[0.02] border border-[rgba(255,255,255,0.06)] flex items-start gap-3 text-xs"
              >
                <div className="mt-0.5 shrink-0">
                  {issue.severity === 'error' ? (
                    <XCircle className="w-4 h-4 text-rose-400" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                  )}
                </div>
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <strong className="text-white">{issue.category}</strong>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-white/5 text-[#8a8a86] font-mono">
                      {issue.count} affected
                    </span>
                  </div>
                  <p className="text-[#8a8a86] leading-relaxed">{issue.description}</p>
                  {issue.columns && issue.columns.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {issue.columns.map((c) => (
                        <span
                          key={c}
                          className="px-1.5 py-0.5 rounded text-[10px] bg-white/5 text-[#f2f2f0] font-mono"
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
