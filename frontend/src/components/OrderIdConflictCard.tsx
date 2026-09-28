import { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Hash,
  Sparkles,
  ShieldAlert,
  Layers,
  RefreshCw,
  Check,
} from 'lucide-react';
import type { OrderIdAnalysisResponse } from '../services/api';
import { generateUniqueOrderIds } from '../services/api';

interface OrderIdConflictCardProps {
  datasetId: string;
  analysis: OrderIdAnalysisResponse | null | undefined;
  onRefresh?: () => void;
  className?: string;
}

export const OrderIdConflictCard = ({
  datasetId,
  analysis,
  onRefresh,
  className = '',
}: OrderIdConflictCardProps) => {
  const [isResolving, setIsResolving] = useState(false);
  const [scope, setScope] = useState<'conflicts_only' | 'all_rows'>('conflicts_only');
  const [prefix, setPrefix] = useState('ORD-');
  const [startNumber, setStartNumber] = useState(1);
  const [showConfig, setShowConfig] = useState(false);
  const [resultMessage, setResultMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!analysis || !analysis.order_id_column) {
    return null;
  }

  const hasConflicts = analysis.has_conflict;
  const isOrderLine = analysis.dataset_structure === 'order_line';
  const conflictCount = analysis.conflicting_order_ids ?? analysis.conflicting_order_ids_count ?? 0;
  const dupCount = analysis.duplicate_order_ids ?? analysis.duplicate_order_ids_count ?? 0;
  const tableRows = analysis.conflict_table || analysis.problematic_ids || [];

  const handleApplyGenerate = async () => {
    setIsResolving(true);
    setErrorMessage(null);
    setResultMessage(null);

    try {
      const res = await generateUniqueOrderIds(datasetId, {
        column: analysis.order_id_column || undefined,
        mode: scope,
        prefix: prefix.trim() || undefined,
        start_number: Number(startNumber) || 1,
      });

      setResultMessage(
        res.after_summary ||
          `Successfully generated unique Order IDs for ${res.affected_rows} rows.`
      );
      setShowConfig(false);
      if (onRefresh) {
        onRefresh();
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to generate unique Order IDs.');
    } finally {
      setIsResolving(false);
    }
  };

  return (
    <div
      className={`rounded-[16px] bg-white/[0.03] border transition-all ${
        hasConflicts
          ? 'border-rose-500/40 bg-gradient-to-b from-rose-500/[0.04] to-transparent'
          : isOrderLine
          ? 'border-sky-500/30 bg-gradient-to-b from-sky-500/[0.03] to-transparent'
          : 'border-emerald-500/30 bg-gradient-to-b from-emerald-500/[0.02] to-transparent'
      } p-6 space-y-6 ${className}`}
    >
      {/* Header and Structure Badge */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[rgba(255,255,255,0.08)]">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Hash className="w-5 h-5 text-[#ff6a3d]" />
            <h3 className="text-base font-bold text-white tracking-tight">
              Order ID Integrity & Structure Analysis
            </h3>
            <span className="text-xs px-2 py-0.5 rounded bg-white/5 text-[#8a8a86] font-mono">
              column: {analysis.order_id_column}
            </span>
          </div>

          <div className="text-xs text-[#8a8a86] flex items-center gap-2">
            <span>Structure Classification:</span>
            {hasConflicts ? (
              <span className="inline-flex items-center gap-1 font-semibold text-rose-400">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Transaction Conflict Detected</span>
              </span>
            ) : isOrderLine ? (
              <span className="inline-flex items-center gap-1 font-semibold text-sky-400">
                <Layers className="w-3.5 h-3.5" />
                <span>Valid Order-Line Data (Multi-item Orders)</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 font-semibold text-emerald-400">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Order-Level Data (1 Row Per Order)</span>
              </span>
            )}
          </div>
        </div>

        {/* Action Button */}
        {hasConflicts && (
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="btn-primary inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-lg shadow-[#ff6a3d]/15 shrink-0"
          >
            <Sparkles className="w-4 h-4" />
            <span>Generate Unique Order IDs</span>
          </button>
        )}
      </div>

      {/* Warning Alert Banner */}
      {hasConflicts && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-xs font-bold text-rose-300 uppercase tracking-wider">
              Data Quality Warning
            </h4>
            <p className="text-sm font-medium text-white">
              Potential Order ID conflict detected: the same Order ID is associated with multiple
              transactions.
            </p>
            <p className="text-xs text-rose-200/80 leading-relaxed">
              Order IDs were found repeated across different transaction dates or customer accounts.
              Review the detailed conflict table below before applying any modifications.
            </p>
          </div>
        </div>
      )}

      {/* Success Notification */}
      {resultMessage && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <p className="text-xs font-medium text-emerald-200">{resultMessage}</p>
        </div>
      )}

      {/* Error Notification */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center gap-3">
          <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <p className="text-xs font-medium text-rose-200">{errorMessage}</p>
        </div>
      )}

      {/* 5 Key Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="p-3 rounded-xl bg-white/[0.02] border border-[rgba(255,255,255,0.06)]">
          <div className="text-[11px] text-[#8a8a86] font-medium">Total Rows</div>
          <div className="text-lg font-bold font-mono text-white mt-0.5">
            {analysis.total_rows.toLocaleString()}
          </div>
        </div>

        <div className="p-3 rounded-xl bg-white/[0.02] border border-[rgba(255,255,255,0.06)]">
          <div className="text-[11px] text-[#8a8a86] font-medium">Unique Order IDs</div>
          <div className="text-lg font-bold font-mono text-white mt-0.5">
            {analysis.unique_order_ids.toLocaleString()}
          </div>
        </div>

        <div className="p-3 rounded-xl bg-white/[0.02] border border-[rgba(255,255,255,0.06)]">
          <div className="text-[11px] text-[#8a8a86] font-medium">Duplicate Order IDs</div>
          <div className={`text-lg font-bold font-mono mt-0.5 ${dupCount > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
            {dupCount.toLocaleString()}
          </div>
        </div>

        <div className="p-3 rounded-xl bg-white/[0.02] border border-[rgba(255,255,255,0.06)]">
          <div className="text-[11px] text-[#8a8a86] font-medium">Conflicting Order IDs</div>
          <div className={`text-lg font-bold font-mono mt-0.5 ${conflictCount > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
            {conflictCount.toLocaleString()}
          </div>
        </div>

        <div className="p-3 rounded-xl bg-white/[0.02] border border-[rgba(255,255,255,0.06)]">
          <div className="text-[11px] text-[#8a8a86] font-medium">Rows Affected</div>
          <div className={`text-lg font-bold font-mono mt-0.5 ${analysis.rows_affected > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
            {analysis.rows_affected.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Safe Generator Configuration Box */}
      {showConfig && (
        <div className="p-5 rounded-xl bg-[#121214] border border-[#ff6a3d]/30 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#ff6a3d]" />
              <span>Safe Order ID Resolution Setup</span>
            </h4>
            <span className="text-[11px] text-[#8a8a86]">Zero silent mutations</span>
          </div>

          <p className="text-xs text-[#8a8a86] leading-relaxed">
            Order IDs will be regenerated sequentially following the standard pattern{' '}
            <code className="text-[#ff6a3d] font-mono">ORD-001</code>. Choose whether to resolve only
            conflicting transaction groups or re-index the entire dataset.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-[11px] font-semibold text-[#8a8a86] uppercase mb-1.5">
                Resolution Scope
              </label>
              <select
                value={scope}
                onChange={(e) => setScope(e.target.value as any)}
                className="w-full px-3 py-2 rounded-xl bg-white/5 border border-[rgba(255,255,255,0.1)] text-white text-xs focus:border-[#ff6a3d] focus:outline-none"
              >
                <option value="conflicts_only">
                  Conflicts Only (Preserves valid order-lines)
                </option>
                <option value="all_rows">All Rows (Complete sequential re-indexing)</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-[#8a8a86] uppercase mb-1.5">
                ID Prefix
              </label>
              <input
                type="text"
                value={prefix}
                onChange={(e) => setPrefix(e.target.value)}
                placeholder="ORD-"
                className="w-full px-3 py-2 rounded-xl bg-white/5 border border-[rgba(255,255,255,0.1)] text-white text-xs font-mono focus:border-[#ff6a3d] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-[#8a8a86] uppercase mb-1.5">
                Starting Number
              </label>
              <input
                type="number"
                min="1"
                value={startNumber}
                onChange={(e) => setStartNumber(parseInt(e.target.value) || 1)}
                className="w-full px-3 py-2 rounded-xl bg-white/5 border border-[rgba(255,255,255,0.1)] text-white text-xs font-mono focus:border-[#ff6a3d] focus:outline-none"
              />
            </div>
          </div>

          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              onClick={() => setShowConfig(false)}
              className="px-4 py-2 rounded-xl text-xs font-medium text-[#8a8a86] hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={handleApplyGenerate}
              disabled={isResolving}
              className="btn-primary inline-flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-semibold"
            >
              {isResolving ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Commit Resolution</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Detailed Problematic Order IDs Table */}
      {tableRows.length > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-[#8a8a86]">
              Problematic & Repeated Order IDs ({tableRows.length})
            </h4>
            <span className="text-[11px] text-[#8a8a86]">
              Categorized by date & product variance
            </span>
          </div>

          <div className="overflow-x-auto rounded-xl border border-[rgba(255,255,255,0.08)] bg-black/20">
            <table className="w-full text-left text-xs">
              <thead className="bg-white/5 text-[#8a8a86] uppercase tracking-wider text-[10px] font-semibold border-b border-[rgba(255,255,255,0.08)]">
                <tr>
                  <th className="px-4 py-3">Order ID</th>
                  <th className="px-4 py-3 text-center">Occurrences</th>
                  <th className="px-4 py-3 text-center">Different Dates</th>
                  <th className="px-4 py-3 text-center">Different Products</th>
                  <th className="px-4 py-3">Dates / Details</th>
                  <th className="px-4 py-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(255,255,255,0.06)]">
                {tableRows.map((row, idx) => (
                  <tr
                    key={idx}
                    className={`hover:bg-white/[0.02] transition-colors ${
                      row.status === 'Conflict' ? 'bg-rose-500/[0.02]' : ''
                    }`}
                  >
                    <td className="px-4 py-3 font-mono font-bold text-white">
                      {row.order_id}
                    </td>
                    <td className="px-4 py-3 text-center font-mono font-semibold text-white">
                      {row.occurrences}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${
                          row.different_dates === 'Yes'
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            : 'bg-white/5 text-[#8a8a86]'
                        }`}
                      >
                        {row.different_dates}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${
                          row.different_products === 'Yes'
                            ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                            : 'bg-white/5 text-[#8a8a86]'
                        }`}
                      >
                        {row.different_products}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#8a8a86] font-mono text-[11px]">
                      {row.dates && row.dates.length > 0 ? row.dates.join(', ') : 'Single date'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {row.status === 'Conflict' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                          <XCircle className="w-3 h-3" />
                          <span>Conflict</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-500/15 text-sky-400 border border-sky-500/30">
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Valid Order-Line</span>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="p-4 rounded-xl bg-white/[0.02] border border-[rgba(255,255,255,0.06)] text-center text-xs text-[#8a8a86]">
          ✓ All Order IDs are unique. No repeated or conflicting IDs detected.
        </div>
      )}
    </div>
  );
};
