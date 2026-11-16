# MartianMap

A desktop map and terrain-aware route planner for Mars' Jezero Crater, built with Python, PyQGIS, PyQt, GDAL, NumPy, and SciPy.

## Setup and launch (Windows)

The locally verified runtime is **QGIS 3.44.15 with its bundled Python 3.12**. Use a QGIS-enabled interpreter: a regular Python installation or an empty virtual environment cannot import `qgis`.

### 1. Install prerequisites

- Install [Git](https://git-scm.com/downloads) and [Git LFS](https://git-lfs.com/).
- Install **QGIS 3.44 LTR**, including its Python environment, from the [QGIS downloads page](https://qgis.org/download/). The [installation guide](https://www.qgis.org/resources/installation-guide/) explains the standalone installer.
- Keep several gigabytes of disk space available for the GIS runtime, input rasters, and generated data. Processing and route searches can also use substantial RAM.

### 2. Download the project and map data

Run in PowerShell:

```powershell
git lfs install
git clone https://github.com/Zain-Im/Martian-Map.git
cd Martian-Map
git lfs pull
git lfs ls-files
```

For an existing clone, run `git lfs pull` inside the repository. TIFF files are stored through Git LFS; downloading only source files or LFS pointer files is insufficient to run the maps.

### 3. Check the QGIS runtime

From the repository root, set the launcher path to match your installation:

```powershell
$qgisPython = "C:\Program Files\QGIS 3.44.15\bin\python-qgis-ltr.bat"
& $qgisPython -c "from qgis.core import Qgis; from qgis.PyQt.QtWidgets import QApplication; from osgeo import gdal; import numpy; from scipy import ndimage; print('QGIS', Qgis.QGIS_VERSION); print('Dependencies OK')"
```

This checks the native SciPy module as well as QGIS and GDAL. If NumPy or SciPy is missing, install the matching packages through your QGIS/OSGeo4W distribution, or use the Conda option below. `requirements.txt` lists NumPy and SciPy; it does **not** install QGIS or configure its native libraries. Avoid mixing packages from unrelated Python/QGIS environments.

### 4. Launch

```powershell
& $qgisPython .\src\main.py
```

Run this from the project root. The current source uses imports resolved from `src`, so use **`python src/main.py`**, not `python -m src.main` or `python main.py`.

On first launch, terrain processing creates `data/processed/traversability_map.tif` before the window opens. Subsequent launches reuse that file. Watch the console for elapsed-time progress and errors; the first launch can take noticeably longer.

### Alternative: Conda / Miniforge

Use one consistent Conda environment if you prefer not to use QGIS Desktop's Python. QGIS packages are maintained by [conda-forge](https://github.com/conda-forge/qgis-feedstock).

```powershell
conda create -n marsmap --override-channels -c conda-forge/label/qgis_ltr -c conda-forge "python=3.12" "qgis=3.44.*" numpy scipy gdal
conda activate marsmap
python -c "import sys; print(sys.executable); from qgis.core import Qgis; from osgeo import gdal; from scipy import ndimage; print('QGIS', Qgis.QGIS_VERSION)"
python src/main.py
```

If `marsmap` already exists, use `conda install -n marsmap` in place of `conda create -n marsmap`. Package availability depends on platform and channel; this fresh environment installation has not been validated as part of the current README update. The QGIS launcher above is the locally verified option.

In VS Code, run the same commands in the terminal. The Run button may use a different Python interpreter; activate `marsmap` and select that environment, or invoke the QGIS batch launcher explicitly.

## Required map files

| Path | Purpose |
| --- | --- |
| `data/raw/elevation_map.tif` | Elevation input; required for terrain generation and geographic context. |
| `data/raw/optical_map.tif` | Optical imagery layer. |
| `data/raw/geology_map.gpkg` | Geological units; missing geology is reported and skipped. |
| `data/processed/traversability_map.tif` | Generated terrain-cost raster; created automatically when absent. |

Paths are resolved relative to the project, not the terminal's working directory. Missing optional layers remain unavailable in the interface. There is no compression/decompression setup step.

The supplied datasets use a Mars coordinate reference system. Elevation processing expects a projected, north-up raster with valid linear units. Routing and displayed route distances assume the supplied projected metre coordinates and aligned raster grids; do not substitute Earth latitude/longitude coordinates or unrelated rasters without preparing their CRS and alignment.

**Regenerating terrain:** close the application and any GIS program using the generated raster, remove `data/processed/traversability_map.tif`, then relaunch. Changing elevation data or processing settings does not automatically invalidate an existing output. Generated rasters are ignored by Git; source TIFFs are tracked through Git LFS.

## Using the application

### Maps and navigation

- Choose **Elevation Map**, **Optical Map**, **Geology Map**, or **Traversability Map** in the sidebar.
- Drag to pan in navigation mode; use the zoom and full-extent controls to adjust the view.
- The legend scrolls as one panel, including layer information and the marker key.
- A translucent black status box at the map's bottom-left shows the current action, selected waypoint, or layer. Coordinates and elevation appear in the bottom bar.
- Unavailable actions are disabled and greyed out.

### Add and manage waypoints

1. Click **Add Waypoint** to enter placement mode.
2. Click the map to preview a waypoint. Each subsequent click moves the same unsaved preview; entered name and description are retained.
3. Click **Save Waypoint** to keep it and return to navigation.
4. Click **Delete Waypoint** during preview to discard it and exit placement mode.

Switching to astronaut placement or route selection also discards an unsaved preview. Select a saved user waypoint to inspect its coordinates, elevation, geology, and traversability, edit its description, or delete it. Descriptions are limited to **250 characters**, with a scrollable editor and character counter; saved user-waypoint description changes apply immediately in memory.

Waypoints are outlined diamonds: orange for user waypoints and purple for predefined landmarks. A selected waypoint becomes a larger gold diamond. The astronaut is an outlined cyan circle.

Eight predefined landmarks are inserted at startup: Rochette, Brac, Issole, Sid, Roubion, Octavia E. Butler Landing Site, Three Forks, and Jezero Delta Front. Their names and descriptions are read-only and they cannot be deleted.

**Session-only data:** user waypoints, descriptions, astronaut location, and routes are currently held in memory. Save Waypoint saves to the current session, not a file; closing the app loses those user-created items.

### Plan a route

1. Click **Set / Update Location**, then click the map to place the astronaut.
2. Click **Plan Route**, then select a destination waypoint.
3. When a route is found, the map fits the entire route and the sidebar shows its horizontal length in metres or kilometres.
4. Moving the astronaut recalculates the route to the same destination. If recalculation fails, the old route is removed.
5. **Clear Route** removes the route and distance summary. Deleting its destination also clears the route.

Route distance follows the returned polyline, including detours; it is not straight-line distance, elevation-adjusted 3D distance, or the terrain-weighted search cost.

## Terrain processing and routing

`src/map_processing.py` generates slope and roughness from elevation, combines their normalized scores, and marks enclosed passable regions as blocked. Defaults are slope weight **0.6**, roughness weight **0.4**, slope limit **20 degrees**, and roughness limit **0** (automatic maximum over valid roughness values). A zero limit selects that terrain measure's map-wide maximum. Score **1** represents blocked terrain; invalid/NoData cells are excluded from routing. The enclosure pass uses four-neighbour connectivity.

`src/pathfinder.py` uses weighted A* with eight-direction movement and prevents diagonal travel through blocked corners. Current defaults are **alpha = 1**, **heuristic weight = 1.25**, and a **64-block LRU raster cache**. It caches validity masks, precomputes movement distances, and reuses neighbouring samples within each expansion.

Important current limitations:

- Weighted A* favours search speed; do not assume a minimum-cost route is guaranteed.
- Search runs synchronously. The progress message is painted before searching, but the interface can remain unresponsive during a long search.
- Large barriers or disconnected areas can require substantial time and RAM. There is no guaranteed runtime cap or verified 20% slowdown bound.
- If the astronaut starts on blocked terrain, the existing escape routine searches toward the destination for up to 100 steps and can prepend blocked cells. This is an escape behaviour, not a guarantee that the entire displayed route is traversable.
- Four-neighbour enclosure processing and eight-direction routing use different connectivity rules.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `ModuleNotFoundError: No module named 'qgis'` | Use the QGIS batch launcher or the activated Conda environment containing QGIS. Check `python -c "import sys; print(sys.executable)"`. Installing only `requirements.txt` is insufficient. |
| Import error for `boot_logging`, `app`, or another local module | Launch `python src/main.py` from the repository root using the configured interpreter. |
| GDAL cannot open a TIFF / file contains Git LFS pointer text | Run `git lfs pull` and confirm the actual raster files were downloaded. |
| `Deleting ...traversability_map.tif failed: Permission denied` | Close QGIS or other programs holding the raster open, and check folder write permissions before regenerating it. |
| SciPy `_nd_image` reports an Application Control policy block | This is a Windows policy restriction, not just a missing import. Use an approved runtime or contact the machine administrator; reinstalling may not resolve the policy block. |
| A map layer is unavailable | Check its exact filename and location in `data/raw/`, then read the console error. |
| Terrain changes do not appear | Remove the old generated raster after closing applications using it, then relaunch to regenerate. |
| No route found / blocked destination | Choose a passable destination and check whether barriers separate it from the astronaut. |

For detailed startup and application logs:

```powershell
$env:MARTIAN_MAP_LOG_LEVEL = "DEBUG"
& $qgisPython .\src\main.py
```

With Conda, use `python src/main.py` instead. Set the variable to `INFO` to restore normal logging. Logs include elapsed boot time, processing stages, layer loading, and exceptions; native QGIS/GDAL messages may use their own format.

## Project structure

```text
Martian-Map/
├── src/
│   ├── main.py                 # Startup, cached terrain generation, QGIS lifecycle
│   ├── app.py                  # Window, actions, waypoint and route workflows
│   ├── map_canvas.py           # Map interaction, markers, route drawing and zoom
│   ├── layer_manager.py        # Layer loading and rendering
│   ├── map_processing.py       # Terrain scores and enclosed-region processing
│   ├── pathfinder.py           # Weighted A* and raster cache
│   ├── permanent_waypoints.py  # Predefined landmarks and descriptions
│   ├── map_legend.py           # Unified scrollable legend
│   ├── description_edit.py     # Character-limited description editor
│   ├── status_label.py         # Resizing map status overlay
│   └── boot_logging.py         # Elapsed-time logging
├── data/
│   ├── raw/                   # Source rasters and geology
│   └── processed/             # Generated traversability (Git-ignored)
├── tests/                     # Development checks
├── requirements.txt           # Python dependencies, excluding QGIS runtime
├── .gitattributes             # Git LFS rules for TIFFs
└── README.md
```

## Development checks

Before launching, use the dependency import check in the setup instructions. `src/test_pathfinder.py` is a manual routing script with hard-coded coordinates and requires the generated raster. Scripts in `tests/` include application checks requiring QGIS and map data; they are not a self-contained, validated test suite. In particular, `tests/test_enclosures.py` still imports the old `src.map_proccesing` filename and needs updating before that test can run.

Develop on a separate branch and review changes before merging. Keep generated rasters out of commits, and use Git LFS when adding or updating source TIFFs.

Agentic AI was used for frontend code, debugging, troubleshooting, and testing of the code.
