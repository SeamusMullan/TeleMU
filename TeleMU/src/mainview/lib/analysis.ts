/**
 * Client-side math functions — ports of scipy/numpy operations used by LMUPI.
 */

// ── Gradient (np.gradient equivalent) ──

export function gradient(values: number[]): number[] {
  const n = values.length;
  if (n < 2) return values.slice();
  const result = new Array<number>(n);
  result[0] = values[1] - values[0];
  result[n - 1] = values[n - 1] - values[n - 2];
  for (let i = 1; i < n - 1; i++) {
    result[i] = (values[i + 1] - values[i - 1]) / 2;
  }
  return result;
}

// ── Correlation ──

export function pearsonR(a: number[], b: number[]): number {
  const n = Math.min(a.length, b.length);
  if (n < 2) return NaN;
  let sumA = 0, sumB = 0;
  for (let i = 0; i < n; i++) { sumA += a[i]; sumB += b[i]; }
  const meanA = sumA / n, meanB = sumB / n;
  let num = 0, denA = 0, denB = 0;
  for (let i = 0; i < n; i++) {
    const da = a[i] - meanA, db = b[i] - meanB;
    num += da * db;
    denA += da * da;
    denB += db * db;
  }
  const den = Math.sqrt(denA * denB);
  return den === 0 ? 0 : num / den;
}

export function spearmanR(a: number[], b: number[]): number {
  const n = Math.min(a.length, b.length);
  if (n < 2) return NaN;
  const rankA = rank(a.slice(0, n));
  const rankB = rank(b.slice(0, n));
  return pearsonR(rankA, rankB);
}

function rank(arr: number[]): number[] {
  const indexed = arr.map((v, i) => ({ v, i }));
  indexed.sort((a, b) => a.v - b.v);
  const ranks = new Array<number>(arr.length);
  let i = 0;
  while (i < indexed.length) {
    let j = i;
    while (j < indexed.length && indexed[j].v === indexed[i].v) j++;
    const avgRank = (i + j - 1) / 2 + 1;
    for (let k = i; k < j; k++) ranks[indexed[k].i] = avgRank;
    i = j;
  }
  return ranks;
}

// ── Cross-correlation (scipy.signal.correlate mode="full") ──

export function crossCorrelate(a: number[], b: number[]): number[] {
  const na = a.length, nb = b.length;
  const out = new Array<number>(na + nb - 1).fill(0);
  for (let lag = 0; lag < out.length; lag++) {
    let sum = 0;
    const offset = lag - nb + 1;
    for (let j = 0; j < nb; j++) {
      const ai = offset + j;
      if (ai >= 0 && ai < na) sum += a[ai] * b[j];
    }
    out[lag] = sum;
  }
  return out;
}

// ── FFT (Cooley-Tukey radix-2 DIT) ──

function nextPow2(n: number): number {
  let p = 1;
  while (p < n) p <<= 1;
  return p;
}

/** Real FFT — returns magnitude array for positive frequencies */
export function rfft(signal: number[]): { re: number[]; im: number[] } {
  const n = nextPow2(signal.length);
  const re = new Array<number>(n).fill(0);
  const im = new Array<number>(n).fill(0);
  for (let i = 0; i < signal.length; i++) re[i] = signal[i];
  fftInPlace(re, im, false);
  const halfN = Math.floor(n / 2) + 1;
  return { re: re.slice(0, halfN), im: im.slice(0, halfN) };
}

export function rfftFreq(n: number, dt: number): number[] {
  const padded = nextPow2(n);
  const halfN = Math.floor(padded / 2) + 1;
  const freq = new Array<number>(halfN);
  for (let i = 0; i < halfN; i++) {
    freq[i] = i / (padded * dt);
  }
  return freq;
}

function fftInPlace(re: number[], im: number[], inverse: boolean): void {
  const n = re.length;
  // Bit reversal
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      [re[i], re[j]] = [re[j], re[i]];
      [im[i], im[j]] = [im[j], im[i]];
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (2 * Math.PI / len) * (inverse ? -1 : 1);
    const wRe = Math.cos(ang), wIm = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let curRe = 1, curIm = 0;
      for (let j = 0; j < len / 2; j++) {
        const uRe = re[i + j], uIm = im[i + j];
        const vRe = re[i + j + len / 2] * curRe - im[i + j + len / 2] * curIm;
        const vIm = re[i + j + len / 2] * curIm + im[i + j + len / 2] * curRe;
        re[i + j] = uRe + vRe;
        im[i + j] = uIm + vIm;
        re[i + j + len / 2] = uRe - vRe;
        im[i + j + len / 2] = uIm - vIm;
        const newCurRe = curRe * wRe - curIm * wIm;
        curIm = curRe * wIm + curIm * wRe;
        curRe = newCurRe;
      }
    }
  }
  if (inverse) {
    for (let i = 0; i < n; i++) { re[i] /= n; im[i] /= n; }
  }
}

// ── Window functions ──

export function hanningWindow(n: number): number[] {
  return Array.from({ length: n }, (_, i) => 0.5 * (1 - Math.cos(2 * Math.PI * i / (n - 1))));
}

export function hammingWindow(n: number): number[] {
  return Array.from({ length: n }, (_, i) => 0.54 - 0.46 * Math.cos(2 * Math.PI * i / (n - 1)));
}

export function blackmanWindow(n: number): number[] {
  return Array.from({ length: n }, (_, i) =>
    0.42 - 0.5 * Math.cos(2 * Math.PI * i / (n - 1)) + 0.08 * Math.cos(4 * Math.PI * i / (n - 1))
  );
}

// ── Rolling statistics ──

export function movingAverage(values: number[], window: number): number[] {
  const n = values.length;
  const result = new Array<number>(n);
  const half = Math.floor(window / 2);
  for (let i = 0; i < n; i++) {
    let sum = 0, count = 0;
    for (let j = Math.max(0, i - half); j <= Math.min(n - 1, i + half); j++) {
      if (!isNaN(values[j])) { sum += values[j]; count++; }
    }
    result[i] = count > 0 ? sum / count : NaN;
  }
  return result;
}

export function rollingStdDev(values: number[], window: number): number[] {
  const mean = movingAverage(values, window);
  const sqMean = movingAverage(values.map((v) => v * v), window);
  return mean.map((m, i) => Math.sqrt(Math.max(sqMean[i] - m * m, 0)));
}

export function maxFilter1d(values: number[], window: number): number[] {
  const n = values.length;
  const half = Math.floor(window / 2);
  return values.map((_, i) => {
    let max = -Infinity;
    for (let j = Math.max(0, i - half); j <= Math.min(n - 1, i + half); j++) {
      if (values[j] > max) max = values[j];
    }
    return max;
  });
}

export function minFilter1d(values: number[], window: number): number[] {
  const n = values.length;
  const half = Math.floor(window / 2);
  return values.map((_, i) => {
    let min = Infinity;
    for (let j = Math.max(0, i - half); j <= Math.min(n - 1, i + half); j++) {
      if (values[j] < min) min = values[j];
    }
    return min;
  });
}

export function medianFilter(values: number[], window: number): number[] {
  const n = values.length;
  const half = Math.floor(window / 2);
  return values.map((_, i) => {
    const windowVals: number[] = [];
    for (let j = Math.max(0, i - half); j <= Math.min(n - 1, i + half); j++) {
      if (!isNaN(values[j])) windowVals.push(values[j]);
    }
    if (windowVals.length === 0) return NaN;
    windowVals.sort((a, b) => a - b);
    const mid = Math.floor(windowVals.length / 2);
    return windowVals.length % 2 !== 0
      ? windowVals[mid]
      : (windowVals[mid - 1] + windowVals[mid]) / 2;
  });
}

// ── Normalization ──

export function normalize01(values: number[]): number[] {
  let min = Infinity, max = -Infinity;
  for (const v of values) {
    if (!isNaN(v)) {
      if (v < min) min = v;
      if (v > max) max = v;
    }
  }
  const range = max - min;
  if (range === 0) return values.map(() => 0);
  return values.map((v) => (v - min) / range);
}

// ── Utility ──

export function median(values: number[]): number {
  const sorted = values.filter((v) => !isNaN(v)).sort((a, b) => a - b);
  if (sorted.length === 0) return 0;
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0
    ? sorted[mid]
    : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function diff(values: number[]): number[] {
  return values.slice(1).map((v, i) => v - values[i]);
}
