import { BrowserWindow, BrowserView, Updater, Utils } from "electrobun/bun";
import type { TeleMURPCSchema } from "../shared/types";
import * as db from "./db";
import { join } from "path";

const DEV_SERVER_PORT = 5173;
const DEV_SERVER_URL = `http://localhost:${DEV_SERVER_PORT}`;

async function getMainViewUrl(): Promise<string> {
  const channel = await Updater.localInfo.channel();
  if (channel === "dev") {
    try {
      await fetch(DEV_SERVER_URL, { method: "HEAD" });
      console.log(`HMR enabled: Using Vite dev server at ${DEV_SERVER_URL}`);
      return DEV_SERVER_URL;
    } catch {
      console.log(
        "Vite dev server not running. Run 'bun run dev:hmr' for HMR support."
      );
    }
  }
  return "views://mainview/index.html";
}

const url = await getMainViewUrl();

const rpc = BrowserView.defineRPC<TeleMURPCSchema>({
  handlers: {
    requests: {
      openFileDialog: async () => {
        const paths = await Utils.openFileDialog({
          startingFolder: "~/",
          allowedFileTypes: "*",
          canChooseFiles: true,
          canChooseDirectory: false,
          allowsMultipleSelection: false,
        });
        return paths.length > 0 && paths[0] !== "" ? paths[0] : null;
      },

      saveFileDialog: async (params) => {
        // Electrobun doesn't have a native save dialog, so we use open dialog
        // to pick a directory and append the filename
        const paths = await Utils.openFileDialog({
          startingFolder: "~/",
          allowedFileTypes: "*",
          canChooseFiles: false,
          canChooseDirectory: true,
          allowsMultipleSelection: false,
        });
        if (paths.length > 0 && paths[0] !== "") {
          return join(paths[0], params!.defaultName);
        }
        return null;
      },

      connect: async (params) => {
        console.log("[RPC] connect called with path:", params!.path);
        await db.connect(params!.path);
        console.log("[RPC] db.connect resolved");
        const tables = await db.listTablesWithCounts();
        console.log("[RPC] listTablesWithCounts returned", tables.length, "tables");
        return { tables };
      },

      disconnect: () => {
        db.disconnect();
      },

      tableSchema: async (params) => {
        return db.tableSchema(params!.table);
      },

      allColumnStats: async (params) => {
        return db.allColumnStats(params!.table);
      },

      previewTable: async (params) => {
        return db.previewTable(params!.table, params!.limit);
      },

      filteredPreview: async (params) => {
        return db.filteredPreview(
          params!.table,
          params!.filters,
          params!.limit
        );
      },

      executeSql: async (params) => {
        return db.executeSql(params!.sql);
      },

      allNumericColumns: async (params) => {
        return db.allNumericColumns(params!.tables);
      },

      fetchColumns: async (params) => {
        return db.fetchColumns(params!.table, params!.columns);
      },

      fetchJoinedColumns: async (params) => {
        return db.fetchJoinedColumns(params!.tableColumns, params!.on);
      },

      exportCsv: async (params) => {
        await db.exportCsv(params!.outputPath, params!.table, params!.sql);
      },

      exportJson: async (params) => {
        await db.exportJson(params!.outputPath, params!.table, params!.sql);
      },
    },
    messages: {},
  },
  maxRequestTime: 300000,
});

const mainWindow = new BrowserWindow({
  title: "TeleMU — Telemetry Explorer",
  url,
  frame: {
    width: 1280,
    height: 800,
    x: 100,
    y: 100,
  },
  rpc,
});

console.log("TeleMU — Telemetry Explorer started!");
