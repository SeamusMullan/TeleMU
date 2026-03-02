import React from "react";
import type { FilterState } from "../lib/filters";

interface FilterGroupProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  showRange?: boolean;
}

export function FilterGroup({ filters, onChange, showRange = true }: FilterGroupProps) {
  const update = (partial: Partial<FilterState>) => {
    onChange({ ...filters, ...partial });
  };

  const parseNum = (val: string): number | null => {
    const n = parseFloat(val);
    return isNaN(n) ? null : n;
  };

  return (
    <div className="space-y-1.5">
      <div className="text-xs font-medium text-telemu-text-dim">Filters</div>
      <label className="flex items-center gap-1.5 text-xs text-telemu-text cursor-pointer">
        <input
          type="checkbox"
          checked={filters.excludeZeros}
          onChange={(e) => update({ excludeZeros: e.target.checked })}
          className="accent-telemu-accent"
        />
        Exclude zeros
      </label>
      <label className="flex items-center gap-1.5 text-xs text-telemu-text cursor-pointer">
        <input
          type="checkbox"
          checked={filters.excludeNaN}
          onChange={(e) => update({ excludeNaN: e.target.checked })}
          className="accent-telemu-accent"
        />
        Exclude NaN
      </label>
      {showRange && (
        <>
          <div className="flex items-center gap-1">
            <span className="text-xs text-telemu-text-dim w-8">From:</span>
            <input
              type="text"
              placeholder="start"
              value={filters.rangeFrom ?? ""}
              onChange={(e) => update({ rangeFrom: parseNum(e.target.value) })}
              className="flex-1 bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text focus:border-telemu-accent outline-none"
            />
          </div>
          <div className="flex items-center gap-1">
            <span className="text-xs text-telemu-text-dim w-8">To:</span>
            <input
              type="text"
              placeholder="end"
              value={filters.rangeTo ?? ""}
              onChange={(e) => update({ rangeTo: parseNum(e.target.value) })}
              className="flex-1 bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text focus:border-telemu-accent outline-none"
            />
          </div>
        </>
      )}
      <div className="flex items-center gap-1">
        <span className="text-xs text-telemu-text-dim w-8">Min:</span>
        <input
          type="text"
          placeholder="min"
          value={filters.valMin ?? ""}
          onChange={(e) => update({ valMin: parseNum(e.target.value) })}
          className="flex-1 bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text focus:border-telemu-accent outline-none"
        />
      </div>
      <div className="flex items-center gap-1">
        <span className="text-xs text-telemu-text-dim w-8">Max:</span>
        <input
          type="text"
          placeholder="max"
          value={filters.valMax ?? ""}
          onChange={(e) => update({ valMax: parseNum(e.target.value) })}
          className="flex-1 bg-telemu-bg-input border border-telemu-border rounded px-1.5 py-0.5 text-xs text-telemu-text focus:border-telemu-accent outline-none"
        />
      </div>
    </div>
  );
}
