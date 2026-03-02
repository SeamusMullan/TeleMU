# LMUPI User Guide

Telemetry Explorer for Le Mans Ultimate racing data.

---

## Getting Started

1. **Open a database** — Use `File > Open` (Ctrl+O), the toolbar Open button, or drag a `.duckdb` file onto the window.
2. The table tree on the left populates with all tables and their row counts.
3. Click any table in the tree to preview it in the Explorer tab.
4. Navigate across five tabs to explore, query, and analyse your telemetry.

### Exporting Data

- `Ctrl+E` exports to CSV, `Ctrl+Shift+E` exports to JSON.
- If the SQL Query tab is active and a query was run, export targets the query results. Otherwise it exports the currently selected table.

---

## Tab 1 — Explorer

Browse raw table data with schema inspection, statistics, and live filtering.

### Controls

| Control | Description |
|---|---|
| Table dropdown | Switch between tables |
| Rows dropdown | Limit preview to 100 / 500 / 1,000 / All |
| Schema sub-tab | Column names, data types, and nullability |
| Statistics sub-tab | Min, max, average, and null count per column |
| Filter bar | One text input per column — type to filter (300ms debounce). Filters combine with AND logic. |
| Clear button | Reset all column filters |

### Quick Start

1. Select a table from the dropdown (or click one in the left tree).
2. Check the Schema tab to understand the data shape.
3. Check Statistics for value ranges and null counts.
4. Type into filter inputs to narrow rows. Use Clear to reset.

> **Tip:** Press `Ctrl+F` from anywhere to jump straight to the filter bar.

---

## Tab 2 — SQL Query

Run arbitrary DuckDB SQL against the loaded database.

### Controls

| Control | Description |
|---|---|
| SQL editor | Multi-line text input (monospace) |
| Run button | Execute the query (`Ctrl+Return`) |
| Status label | Row count + elapsed time on success, or error message |
| Results table | Query output |

### Quick Start

1. Type any valid DuckDB SQL (SELECT, aggregations, window functions, JOINs, etc.).
2. Press `Ctrl+Return` or click Run.
3. Results appear below. Export them with `Ctrl+E` while this tab is active.

### Example Queries

```sql
-- Compare two signals side by side
SELECT a.ts, a.value AS speed, b.value AS throttle
FROM speed a JOIN throttle b ON a.ts = b.ts

-- Find peak values
SELECT MAX(value) AS peak_speed FROM speed

-- Time-window analysis
SELECT ts, value FROM brake WHERE ts BETWEEN 100 AND 200
```

---

## Tab 3 — Signal Analyzer

Multi-signal comparison plotting with six plot types.

### Sidebar Controls

| Control | Description |
|---|---|
| Signal tree | Check tables and columns to plot. Tables without `ts` appear in yellow. |
| X axis | `ts` (time) or `(row index)` |
| Type | Line, Scatter, Histogram, Correlation Matrix, Cross-Correlation, Correlation Finder |
| Normalize (0-1) | Min-max normalise each signal to the 0-1 range |
| Exclude zeros | Drop rows where any Y value is 0 |
| Exclude NaN | Drop rows with NaN values |
| From / To | X-axis range filter |
| Min / Max | Y-value clamp — rows outside this range are excluded |

### Plot Types

**Line** — Standard time-series overlay. When exactly 2 signals have ranges differing by more than 10x, a dual Y-axis is used automatically.

**Scatter** — Point cloud with small markers (size 4, 70% opacity).

**Histogram** — Overlapping frequency distributions, 50 bins per signal.

**Correlation Matrix** — Heatmap of Pearson r values between all selected signals. Requires 2+ signals.

**Cross-Correlation** — Lag analysis between exactly 2 signals. Shows the peak lag and correlation coefficient. Useful for finding time delays between related signals.

**Correlation Finder** — Automatic discovery mode. Scans every signal pair across all loaded tables, computes Pearson and Spearman correlations, and displays the top 20 pairs as a bar chart. No manual signal selection needed.

### Quick Start

1. Check one or more signals in the tree.
2. Select a plot type and X axis.
3. Optionally set filters or enable normalization.
4. Click Plot.
5. Use the Matplotlib toolbar above the plot to pan, zoom, or save the figure.

### Multi-Table Joining

- Tables with `ts` are joined on timestamp when X = `ts`.
- Tables without `ts` are row-aligned (truncated to the shortest table).
- Column names are prefixed with their table name (e.g. `speed.value`).

---

## Tab 4 — Track Viewer

Plot the GPS track as a 2D map, optionally coloured by any signal.

### How It Works

The viewer automatically finds GPS tables by matching table names:

| Data | Recognised table names |
|---|---|
| Latitude | `latitude`, `lat`, `gps_lat`, `gps latitude`, `gpslat`, `gps_latitude` |
| Longitude | `longitude`, `lon`, `lng`, `gps_lon`, `gps longitude`, `gpslon`, `gpslng`, `gps_longitude` |
| Speed (optional) | `speed`, `gps speed`, `gps_speed`, `gpsspeed`, `velocity` |

Name matching is case-insensitive.

### Sidebar Controls

| Control | Description |
|---|---|
| Colour-by Signal tree | Check a signal to colour the track line by its values |
| Exclude zeros | Remove points where the colour signal is 0 |
| Exclude NaN | Remove points with NaN colour values |
| Min / Max | Clamp the colour signal range |

### Quick Start

1. Ensure your database has latitude and longitude tables (see naming above).
2. Click Plot for a plain track outline. Start = green circle, finish = red square.
3. Check a signal (e.g. speed) in the tree and click Plot again to see the track coloured by that signal. A colour bar shows the value range.

### Colour-By Behaviour

- No signal checked: single-colour track line.
- Signal checked: track segments are coloured using the `plasma` colourmap. Only the first checked signal is used.
- Filters apply to the colour signal values, not the GPS coordinates.

> **Tip:** Use "Exclude zeros" to hide GPS dropout points that show up as (0, 0).

---

## Tab 5 — Advanced Analysis

Four specialised analysis types for deeper signal processing.

### Shared Controls

| Control | Description |
|---|---|
| Signal tree | Check signals (used by FFT and Rolling Statistics) |
| X axis | `ts` or `(row index)` |
| Analysis dropdown | Switches the controls panel and analysis type |
| From / To | Time-range filter on the ts axis |

The Controls section below the Analysis dropdown changes based on the selected type.

---

### Derived Signal

Compute a new signal by combining two source tables with an operator.

| Control | Description |
|---|---|
| Signal A | First operand (table dropdown) |
| Operator | `+`, `-`, `*`, `/`, `d/dt` |
| Signal B | Second operand (disabled for `d/dt`) |
| Plot original signals too | Overlay the source signals alongside the result |

**Operators:**
- `+`, `-`, `*` — Element-wise arithmetic, aligned by row position.
- `/` — Division with NaN where denominator is 0.
- `d/dt` — Time derivative using `numpy.gradient`. Uses a dual Y-axis when plotting originals.

**Example uses:**
- Compute power: `force * velocity`
- Compute slip ratio: `(wheel_speed - vehicle_speed) / vehicle_speed`
- Compute acceleration: `d/dt` of speed

---

### Lap Comparison

Split a signal into laps using a boolean marker and overlay all laps on one plot.

| Control | Description |
|---|---|
| Lap Marker | Boolean signal table — nonzero values = True |
| Detect Laps | Finds rising edges (False to True transitions) with 10s debounce |
| Lap count label | Shows how many laps were found |
| Signal to Compare | The signal to plot per-lap |
| Normalize lap time (0-1) | Scale each lap's X axis to 0-1 for direct comparison |

**Workflow:**
1. Select the lap marker table (e.g. a lap trigger or sector signal).
2. Click **Detect Laps** and verify the lap count.
3. Select the signal to compare (e.g. speed, throttle).
4. Enable "Normalize lap time" to align laps of different durations.
5. Click Analyze.

Each lap is colour-coded and labelled with its duration in the legend.

> **Tip:** Normalization is essential for comparing laps of different lengths — without it, shorter laps appear compressed on the left side.

---

### FFT / Spectral

Frequency domain analysis of a single signal.

| Control | Description |
|---|---|
| Window | None (rectangular), Hanning, Hamming, or Blackman |
| Log scale (dB) | Display magnitude in decibels |
| Max frequency (Hz) | Truncate the frequency axis (leave empty for full Nyquist range) |

**How it works:**
- Sample rate is estimated from `1 / median(diff(ts))`.
- The signal mean is subtracted (DC removal) before windowing.
- Uses `scipy.fft.rfft` for the single-sided amplitude spectrum.

**Requires exactly 1 signal** checked in the tree.

**Example uses:**
- Identify vibration frequencies in suspension data
- Find periodic noise in sensor signals
- Verify sample rate consistency

> **Tip:** Use Hanning window as a safe default — it reduces spectral leakage for most signals. Use the From/To filter to isolate a specific time segment.

---

### Rolling Statistics

Apply sliding-window statistics to one or more signals.

| Control | Description |
|---|---|
| Window size | 3 to 10,000 samples (default 50) |
| Statistic | Moving Average, Rolling Std Dev, Upper Envelope, Lower Envelope, Median Filter |
| Show original signal | Overlay the raw signal at 30% opacity |

**Statistics:**

| Statistic | What it shows |
|---|---|
| Moving Average | Smoothed signal trend |
| Rolling Std Dev | Local variability / noise level |
| Upper Envelope | Signal peaks over the window |
| Lower Envelope | Signal valleys over the window |
| Median Filter | Noise removal preserving edges |

Multiple signals can be processed at once — each gets its own colour.

**Example uses:**
- Smooth noisy throttle or brake signals with Moving Average
- Find peak cornering speeds with Upper Envelope
- Measure signal noise with Rolling Std Dev
- Clean up outliers with Median Filter

> **Tip:** Window size is in samples, not seconds. If your data is at 60 Hz, a window of 60 covers 1 second.

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open database file |
| `Ctrl+E` | Export CSV |
| `Ctrl+Shift+E` | Export JSON |
| `Ctrl+F` | Focus Explorer filter bar |
| `Ctrl+G` | Switch to Signal Analyzer |
| `Ctrl+Return` | Run SQL query (in SQL tab) |
| `Ctrl+Q` | Quit |

---

## Tips

- **Drag and drop** any `.duckdb` file onto the window to open it.
- **Recent files** are remembered across sessions (up to 10) in the File menu.
- **Matplotlib toolbar** in all plot tabs provides pan, zoom, home reset, and save-to-file.
- **All data is read-only** — the database is never modified.
- Tables without a `ts` column are marked in yellow and cannot be time-joined with other tables.
