/** Widget registration — side-effect imports to register all widget types. */

import { setDefaultProfileFactory } from "../stores/layoutStore";
import { createDefaultProfile } from "./defaults";

// Register the default profile factory before any store initialization
setDefaultProfileFactory(createDefaultProfile);

// Dashboard widgets
import "./types/gauge";
import "./types/sparkline";
import "./types/status-row";
import "./types/lap-info";
import "./types/recording";
import "./types/streaming";
import "./types/text-label";

// Explorer widgets
import "./types/session-picker";
import "./types/schema-browser";
import "./types/data-table";
import "./types/sql-query";

// Analyzer widgets
import "./types/echart";
import "./types/channel-selector";
