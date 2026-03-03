/** Signal analyzer — line, scatter, histogram, correlation plots. */

export default function AnalyzerPage() {
  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-bold">Signal Analyzer</h1>
      <p className="text-neutral-500">
        Select signals to visualize with ECharts plots.
      </p>
      {/* TODO: v0.2.0 — ECharts plot types, signal tree */}
    </div>
  );
}
