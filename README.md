# MartianMap

A desktop Martian mapping application developed
using Python, PyQGIS and PyQt.

The application aims to combine multiple geographic
datasets of Mars into one interactive map.

## Features

- Display Martian geographic datasets.
- Overlay multiple map layers.
- Load raster and vector datasets.
- Zoom and navigate around the map.
- Manage map layers.
- Support future terrain analysis and navigation features.

## Technologies

- Python
- PyQGIS
- PyQt
- QGIS
- Git and GitHub

## Project Structure

```text
MartianMap/
│
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── app.py
│   ├── map_canvas.py
│   ├── layer_manager.py
│   ├── map_controls.py
│   └── map_proccesing.py
│
├── data/
│   ├── raw/
│   └── processed/
│
├── requirements.txt
├── README.md
└── .gitignore
```

## Installation

### 1. Install QGIS

Download QGIS from:

https://qgis.org/

Both developers should use the same QGIS version.

### 2. Clone the repository

```bash
git clone YOUR_REPOSITORY_URL
cd MartianMap
```

### 3. Run the application

Use a Python environment configured for PyQGIS, such as the QGIS
installation's environment or the configured `marsmap` Conda environment.

On Windows, open the OSGeo4W Shell,
navigate to the repository and run:

```bash
python -m src.main
```

Do not use an ordinary Python interpreter
unless it has been configured for PyQGIS.

In PowerShell with the configured Conda environment, run from the repository root:

```powershell
conda activate marsmap
python -m src.main
```

Use the module command above rather than running `src/main.py` directly;
the application uses package-relative imports.

## Map Data

Place `elevation_map.tif` and `optical_map.tif` in `data/raw/`.
Startup reads the elevation TIFF directly and generates `Traversability.tif`
in the same directory. No separate compression or decompression step is required.

All displayed layers are loaded from `data/raw/`. Place the optional
`geology_map.gpkg` there as well; a missing geology layer is reported and
skipped. These paths are relative to the repository root, not `src/`.

Supported formats currently include:

- GeoTIFF (.tif, .tiff)
- GeoPackage (.gpkg)
- GeoJSON (.geojson)
- Shapefile (.shp)

All datasets must use compatible geographic
coordinate reference systems to overlay correctly.

## Team Development

This project is developed by a team of two.

Suggested branches:

- main
- feature/map-gis
- feature/interface

Developers should work on separate branches
and merge changes through pull requests.

## Development Status

Startup logs show elapsed seconds since boot, severity, component, and stage
durations. They cover imports, terrain processing, QGIS initialization, UI
construction, layer loading, predefined waypoints, first render, and shutdown.
Missing layers are warnings; invalid layers and unhandled exceptions are errors
with diagnostic details (unhandled exceptions include tracebacks).

For additional diagnostics in PowerShell:

```powershell
$env:MARTIAN_MAP_LOG_LEVEL = "DEBUG"
python src/main.py
```

Use `INFO` instead of `DEBUG` to restore normal verbosity. Native QGIS/GDAL/PROJ
messages may still appear in their original format.

Initial project structure created.

Current implementation includes:

- Basic desktop application window.
- QGIS map canvas.
- Raster and vector layer loading functions.
- Basic zoom controls.

Future development:

- Interactive layer selection.
- Layer visibility controls.
- Martian coordinate system configuration.
- Elevation visualization.
- Terrain analysis.
- Route planning.
