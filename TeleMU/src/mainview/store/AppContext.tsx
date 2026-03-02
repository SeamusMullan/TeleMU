import React, { createContext, useContext, useReducer } from "react";
import type { TableInfo, TableColumnMap } from "../../shared/types";

export type TabId =
  | "explorer"
  | "sql"
  | "analyzer"
  | "track"
  | "advanced";

interface AppState {
  connected: boolean;
  dbFileName: string;
  dbPath: string;
  tables: TableInfo[];
  currentTable: string | null;
  activeTab: TabId;
  numericColumns: TableColumnMap;
  tablesWithTs: Set<string>;
}

type Action =
  | { type: "CONNECT"; payload: { path: string; fileName: string; tables: TableInfo[] } }
  | { type: "DISCONNECT" }
  | { type: "SET_TABLE"; payload: string }
  | { type: "SET_TAB"; payload: TabId }
  | { type: "SET_NUMERIC_COLUMNS"; payload: TableColumnMap }
  | { type: "SET_TABLES_WITH_TS"; payload: Set<string> };

const initialState: AppState = {
  connected: false,
  dbFileName: "",
  dbPath: "",
  tables: [],
  currentTable: null,
  activeTab: "explorer",
  numericColumns: {},
  tablesWithTs: new Set(),
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "CONNECT":
      return {
        ...state,
        connected: true,
        dbPath: action.payload.path,
        dbFileName: action.payload.fileName,
        tables: action.payload.tables,
        currentTable: action.payload.tables[0]?.name ?? null,
      };
    case "DISCONNECT":
      return { ...initialState };
    case "SET_TABLE":
      return { ...state, currentTable: action.payload };
    case "SET_TAB":
      return { ...state, activeTab: action.payload };
    case "SET_NUMERIC_COLUMNS":
      return { ...state, numericColumns: action.payload };
    case "SET_TABLES_WITH_TS":
      return { ...state, tablesWithTs: action.payload };
    default:
      return state;
  }
}

const AppContext = createContext<{
  state: AppState;
  dispatch: React.Dispatch<Action>;
}>({ state: initialState, dispatch: () => {} });

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  return useContext(AppContext);
}
