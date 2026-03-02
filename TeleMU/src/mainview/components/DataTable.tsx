import React from "react";

interface DataTableProps {
  columns: string[];
  rows: unknown[][];
  maxHeight?: string;
}

export function DataTable({ columns, rows, maxHeight = "100%" }: DataTableProps) {
  if (columns.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-telemu-text-dim text-sm">
        No data
      </div>
    );
  }

  return (
    <div className="overflow-auto border border-telemu-border rounded" style={{ maxHeight }}>
      <table className="w-full text-sm border-collapse">
        <thead className="sticky top-0 z-10">
          <tr>
            {columns.map((col, i) => (
              <th
                key={i}
                className="bg-telemu-bg-light text-telemu-text-bright font-semibold text-left px-2 py-1.5 border-b border-r border-telemu-border whitespace-nowrap"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr
              key={ri}
              className={`${
                ri % 2 === 0 ? "bg-telemu-bg" : "bg-telemu-bg-light"
              } hover:bg-telemu-selection`}
            >
              {row.map((val, ci) => (
                <td
                  key={ci}
                  className="px-2 py-1 border-r border-telemu-border text-telemu-text whitespace-nowrap max-w-[300px] truncate"
                >
                  {val != null ? String(val) : ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
