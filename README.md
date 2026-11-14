
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
├── main.py
├── app.py
├── map_canvas.py
├── layer_manager.py
├── map_controls.py
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

PyQGIS requires the Python environment
provided by the QGIS installation.

On Windows, open the OSGeo4W Shell,
navigate to the repository and run:

```bash
python main.py
```

Do not use an ordinary Python interpreter
unless it has been configured for PyQGIS.

## Map Data

Place original downloaded datasets in:

`data/raw/`

Place prepared datasets in:

`data/processed/`

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
