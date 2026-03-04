/** Virtualized data table for exploring table contents. */

import { useState, useEffect, useMemo, useRef } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useSessionStore } from "../../stores/sessionStore";
import { api } from "../../api/rest";

interface TableData {
  columns: string[];
  rows: unknown[][];
  row_count: number;
}

const columnHelper = createColumnHelper<unknown[]>();

export default function DataTable() {
  const { tables, activeSession } = useSessionStore();
  const [selectedTable, setSelectedTable] = useState<string>("");
  const [data, setData] = useState<TableData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const parentRef = useRef<HTMLDivElement>(null);

  // Auto-select first table
  useEffect(() => {
    if (tables.length > 0 && !selectedTable) {
      setSelectedTable(tables[0]!.name);
    }
  }, [tables, selectedTable]);

  // Fetch data when table changes
  useEffect(() => {
    if (!selectedTable || !activeSession) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    api
      .data(selectedTable, 1000)
      .then((d) => setData(d as TableData))
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [selectedTable, activeSession]);

  const columns = useMemo(() => {
    if (!data) return [];
    return data.columns.map((col, i) =>
      columnHelper.accessor((row: unknown[]) => row[i], {
        id: col,
        header: col,
        cell: (info) => {
          const val = info.getValue();
          if (val === null) return <span className="text-neutral-600">NULL</span>;
          return String(val);
        },
      }),
    );
  }, [data]);

  const table = useReactTable({
    data: data?.rows ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const { rows } = table.getRowModel();

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 32,
    overscan: 10,
  });

  if (!activeSession) {
    return (
      <div className="flex h-full items-center justify-center p-3 text-xs text-neutral-500">
        Open a session to view data
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Table selector */}
      <div className="flex items-center gap-2 border-b border-neutral-800 px-3 py-2">
        <select
          value={selectedTable}
          onChange={(e) => setSelectedTable(e.target.value)}
          className="rounded border border-neutral-600 bg-neutral-800 px-2 py-1 text-xs text-neutral-200 outline-none"
        >
          <option value="">Select table...</option>
          {tables.map((t) => (
            <option key={t.name} value={t.name}>{t.name}</option>
          ))}
        </select>
        {data && (
          <span className="text-xs text-neutral-500">
            {data.row_count} rows, {data.columns.length} cols
          </span>
        )}
        {loading && <span className="text-xs text-neutral-500">Loading...</span>}
      </div>

      {error && <div className="px-3 py-1 text-xs text-red-400">{error}</div>}

      {/* Virtualized table */}
      <div ref={parentRef} className="flex-1 overflow-auto">
        {data && (
          <table className="w-full border-collapse text-xs">
            <thead className="sticky top-0 z-10 bg-neutral-800">
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      className="border-b border-neutral-700 px-2 py-1.5 text-left font-mono font-bold text-neutral-300"
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {virtualizer.getVirtualItems().length > 0 && (
                <tr>
                  <td
                    colSpan={columns.length}
                    style={{ height: virtualizer.getVirtualItems()[0]?.start ?? 0 }}
                  />
                </tr>
              )}
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const row = rows[virtualRow.index]!;
                return (
                  <tr key={row.id} className="hover:bg-neutral-800/50">
                    {row.getVisibleCells().map((cell) => (
                      <td
                        key={cell.id}
                        className="border-b border-neutral-800/50 px-2 py-1 font-mono text-neutral-400"
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                );
              })}
              {virtualizer.getVirtualItems().length > 0 && (
                <tr>
                  <td
                    colSpan={columns.length}
                    style={{
                      height:
                        virtualizer.getTotalSize() -
                        (virtualizer.getVirtualItems().at(-1)?.end ?? 0),
                    }}
                  />
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
