/** Data explorer — table browser, schema view, data preview. */

export default function ExplorerPage() {
  return (
    <div className="p-4">
      <h1 className="mb-4 text-lg font-bold">Data Explorer</h1>
      <p className="text-neutral-500">
        Open a .duckdb session file to explore telemetry data.
      </p>
      {/* TODO: v0.2.0 — DataTable, schema view, filter bar */}
    </div>
  );
}
