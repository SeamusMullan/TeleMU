export interface FilterState {
  excludeZeros: boolean;
  excludeNaN: boolean;
  rangeFrom: number | null;
  rangeTo: number | null;
  valMin: number | null;
  valMax: number | null;
}

export const DEFAULT_FILTERS: FilterState = {
  excludeZeros: false,
  excludeNaN: false,
  rangeFrom: null,
  rangeTo: null,
  valMin: null,
  valMax: null,
};

/** Convert a value to number, handling null/undefined → NaN */
export function toFloat(val: unknown): number {
  if (val == null) return NaN;
  if (val instanceof Date) return val.getTime() / 1000;
  const n = Number(val);
  return n;
}

/**
 * Apply filters to parallel arrays of data.
 * x: the x-axis data (or null for row index mode).
 * yArrays: map of name → numeric values.
 * Returns { x, yArrays, excluded } with filtered data and count of excluded rows.
 */
export function applyFilters(
  x: number[] | null,
  yArrays: Record<string, number[]>,
  filters: FilterState
): { x: number[]; yArrays: Record<string, number[]>; excluded: number } {
  const keys = Object.keys(yArrays);
  if (keys.length === 0) return { x: x ?? [], yArrays, excluded: 0 };

  const n = yArrays[keys[0]].length;
  const mask = new Uint8Array(n).fill(1);
  const xArr = x ?? Array.from({ length: n }, (_, i) => i);

  // Range filter on X
  if (filters.rangeFrom !== null) {
    for (let i = 0; i < n; i++) {
      if (xArr[i] < filters.rangeFrom!) mask[i] = 0;
    }
  }
  if (filters.rangeTo !== null) {
    for (let i = 0; i < n; i++) {
      if (xArr[i] > filters.rangeTo!) mask[i] = 0;
    }
  }

  // Value clamp (min/max)
  if (filters.valMin !== null) {
    for (let i = 0; i < n; i++) {
      if (!mask[i]) continue;
      const allNaN = keys.every((k) => isNaN(yArrays[k][i]));
      if (allNaN) continue;
      const rowMin = Math.min(...keys.map((k) => yArrays[k][i]).filter((v) => !isNaN(v)));
      if (rowMin < filters.valMin!) mask[i] = 0;
    }
  }
  if (filters.valMax !== null) {
    for (let i = 0; i < n; i++) {
      if (!mask[i]) continue;
      const allNaN = keys.every((k) => isNaN(yArrays[k][i]));
      if (allNaN) continue;
      const rowMax = Math.max(...keys.map((k) => yArrays[k][i]).filter((v) => !isNaN(v)));
      if (rowMax > filters.valMax!) mask[i] = 0;
    }
  }

  // Exclude NaN
  if (filters.excludeNaN) {
    for (let i = 0; i < n; i++) {
      if (!mask[i]) continue;
      if (keys.some((k) => isNaN(yArrays[k][i]))) mask[i] = 0;
    }
  }

  // Exclude zeros
  if (filters.excludeZeros) {
    for (let i = 0; i < n; i++) {
      if (!mask[i]) continue;
      if (keys.some((k) => yArrays[k][i] === 0)) mask[i] = 0;
    }
  }

  // Build filtered output
  const filteredX: number[] = [];
  const filteredY: Record<string, number[]> = {};
  for (const k of keys) filteredY[k] = [];

  let excluded = 0;
  for (let i = 0; i < n; i++) {
    if (mask[i]) {
      filteredX.push(xArr[i]);
      for (const k of keys) filteredY[k].push(yArrays[k][i]);
    } else {
      excluded++;
    }
  }

  return { x: filteredX, yArrays: filteredY, excluded };
}
