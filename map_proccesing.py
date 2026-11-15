from osgeo import gdal
from pathlib import Path
import numpy as np

gdal.UseExceptions()

SLOPE_WEIGHT = 0.6
ROUGHNESS_WEIGHT = 0.4

PROJECT_DIR = Path(__file__).resolve().parent
INPUT = PROJECT_DIR / "maps" / "MissionArea2.tif"
OUTPUT = PROJECT_DIR / "maps" / "Traversability.tif"

SLOPE_LIMIT = 20
ROUGHNESS_LIMIT = 0
NODATA = -9999.0
BLOCK_SIZE = 512
# Elevations are assumed to be metres; change this for another vertical unit.
ELEVATION_UNIT_METRES = 1.0


def validate_settings():
    for name, value in (("SLOPE_LIMIT", SLOPE_LIMIT),
                        ("ROUGHNESS_LIMIT", ROUGHNESS_LIMIT),
                        ("SLOPE_WEIGHT", SLOPE_WEIGHT),
                        ("ROUGHNESS_WEIGHT", ROUGHNESS_WEIGHT)):
        if not np.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and non-negative")
    if not np.isclose(SLOPE_WEIGHT + ROUGHNESS_WEIGHT, 1.0):
        raise ValueError("Weights must add to 1")
    if not isinstance(BLOCK_SIZE, int) or BLOCK_SIZE <= 0:
        raise ValueError("BLOCK_SIZE must be a positive integer")
    if not np.isfinite(ELEVATION_UNIT_METRES) or ELEVATION_UNIT_METRES <= 0:
        raise ValueError("ELEVATION_UNIT_METRES must be finite and positive")

def calculate_terrain(dem):
    """Generate slope and roughness rasters in memory."""
    srs = dem.GetSpatialRef()
    if srs is None or not srs.IsProjected():
        raise ValueError("DEM must have a projected CRS with linear units")
    transform = dem.GetGeoTransform()
    if transform[2] != 0 or transform[4] != 0:
        raise ValueError("Reproject rotated DEM grids before terrain processing")
    if transform[1] <= 0 or transform[5] >= 0:
        raise ValueError("DEM must use a north-up grid with nonzero pixel size")
    band = dem.GetRasterBand(1)
    if band.GetScale() not in (None, 1.0) or band.GetOffset() not in (None, 0.0):
        raise ValueError("Apply DEM band scale/offset before terrain processing")

    slope = gdal.DEMProcessing(
        "",
        dem,
        "slope",
        format="MEM",
        scale=srs.GetLinearUnits() / ELEVATION_UNIT_METRES
    )

    roughness = gdal.DEMProcessing(
        "",
        dem,
        "roughness",
        format="MEM"
    )

    if slope is None or roughness is None:
        raise RuntimeError("GDAL could not calculate terrain derivatives")
    return slope, roughness

def normalize(array, maximum):
    """Normalize to [0, 1], using the array maximum when the limit is zero."""
    array = np.asarray(array)
    if not np.isfinite(maximum) or maximum < 0:
        raise ValueError("Normalization limit must be finite and non-negative")
    if array.size == 0:
        return np.empty_like(array, dtype=float)
    if not np.all(np.isfinite(array)) or np.any(array < 0):
        raise ValueError("Normalize only valid, non-negative terrain values")
    if maximum == 0:
        maximum = np.max(array)
    if maximum == 0:
        return np.zeros_like(array, dtype=float)
    return np.clip(array / maximum, 0, 1)


def calculate_cost(slope_array, roughness_array, slope_limit=None, roughness_limit=None):
    """Return weighted difficulty, forcing 1 when either effective limit is exceeded."""
    if np.shape(slope_array) != np.shape(roughness_array):
        raise ValueError("Slope and roughness arrays must have matching shapes")

    slope_array = np.asarray(slope_array)
    roughness_array = np.asarray(roughness_array)
    slope_limit = SLOPE_LIMIT if slope_limit is None else slope_limit
    roughness_limit = ROUGHNESS_LIMIT if roughness_limit is None else roughness_limit
    slope_normalized = normalize(slope_array, slope_limit)
    roughness_normalized = normalize(roughness_array, roughness_limit)
    if slope_limit == 0 and slope_array.size:
        slope_limit = np.max(slope_array)
    if roughness_limit == 0 and roughness_array.size:
        roughness_limit = np.max(roughness_array)

    cost = (
        SLOPE_WEIGHT * slope_normalized
        + ROUGHNESS_WEIGHT * roughness_normalized
    )
    exceeds_limit = (slope_array > slope_limit) | (roughness_array > roughness_limit)
    return np.where(exceeds_limit, 1.0, cost)

def terrain_blocks(slope, roughness):
    """Yield aligned arrays and their shared valid-data mask."""
    bands = [slope.GetRasterBand(1), roughness.GetRasterBand(1)]
    for y in range(0, slope.RasterYSize, BLOCK_SIZE):
        for x in range(0, slope.RasterXSize, BLOCK_SIZE):
            w = min(BLOCK_SIZE, slope.RasterXSize - x)
            h = min(BLOCK_SIZE, slope.RasterYSize - y)
            arrays = [band.ReadAsArray(x, y, w, h) for band in bands]
            if any(array is None for array in arrays):
                raise RuntimeError(f"Could not read raster block at {x}, {y}")
            valid = np.ones((h, w), dtype=bool)
            for band, array in zip(bands, arrays):
                valid &= np.isfinite(array) & (array >= 0)
                nodata = band.GetNoDataValue()
                if nodata is not None:
                    valid &= array != nodata
                valid &= band.GetMaskBand().ReadAsArray(x, y, w, h) != 0
            yield x, y, arrays[0], arrays[1], valid


def create_traversability(slope, roughness, output_path):
    validate_settings()
    if (slope.RasterXSize, slope.RasterYSize, slope.GetGeoTransform(), slope.GetProjection()) != (
        roughness.RasterXSize, roughness.RasterYSize, roughness.GetGeoTransform(), roughness.GetProjection()
    ):
        raise ValueError("Slope and roughness rasters must use the same grid and CRS")

    # Resolve automatic limits once over the entire map, never per output block.
    slope_limit, roughness_limit = SLOPE_LIMIT, ROUGHNESS_LIMIT
    has_valid = False
    for _, _, slope_array, roughness_array, valid in terrain_blocks(slope, roughness):
        if np.any(valid):
            has_valid = True
            if SLOPE_LIMIT == 0:
                slope_limit = max(slope_limit, float(np.max(slope_array[valid])))
            if ROUGHNESS_LIMIT == 0:
                roughness_limit = max(roughness_limit, float(np.max(roughness_array[valid])))
    if not has_valid:
        raise ValueError("No valid terrain pixels to process")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    width = slope.RasterXSize
    height = slope.RasterYSize

    driver = gdal.GetDriverByName("GTiff")
    if driver is None:
        raise RuntimeError("GDAL GeoTIFF driver is unavailable")

    output = driver.Create(
        str(output_path),
        width,
        height,
        1,
        gdal.GDT_Float32,
        options=[
            "TILED=YES",
            "COMPRESS=DEFLATE",
            "PREDICTOR=3",
            "BIGTIFF=IF_SAFER"
        ]
    )
    if output is None:
        raise RuntimeError(f"Could not create {output_path}")

    # Preserve geographic information
    output.SetGeoTransform(slope.GetGeoTransform())
    output.SetProjection(slope.GetProjection())

    slope_band = slope.GetRasterBand(1)
    roughness_band = roughness.GetRasterBand(1)
    output_band = output.GetRasterBand(1)

    output_band.SetNoDataValue(NODATA)

    output_band.SetDescription("Terrain difficulty: 0=easiest, 1=hardest")
    output.SetMetadata({
        "SLOPE_NORMALIZATION_LIMIT": str(slope_limit),
        "ROUGHNESS_NORMALIZATION_LIMIT": str(roughness_limit),
        "SLOPE_WEIGHT": str(SLOPE_WEIGHT),
        "ROUGHNESS_WEIGHT": str(ROUGHNESS_WEIGHT),
    })
    try:
        for x, y, slope_array, roughness_array, valid in terrain_blocks(slope, roughness):
            cost = np.full(slope_array.shape, NODATA, dtype=np.float32)
            if np.any(valid):
                cost[valid] = calculate_cost(
                    slope_array[valid], roughness_array[valid],
                    slope_limit, roughness_limit
                )
            output_band.WriteArray(cost, x, y)
        output.FlushCache()
    finally:
        output_band = None
        output = None
    return output_path


def main():

    validate_settings()
    if Path(INPUT).resolve() == Path(OUTPUT).resolve():
        raise ValueError("Input and output paths must differ")
    dem = gdal.Open(str(INPUT), gdal.GA_ReadOnly)
    if dem is None or dem.RasterCount != 1:
        raise ValueError("Input must be a single-band elevation raster")

    print("Calculating slope and roughness...")

    slope, roughness = calculate_terrain(dem)

    print("Calculating traversability...")

    saved_path = create_traversability(slope, roughness, OUTPUT)

    # Release in-memory rasters
    slope = None
    roughness = None
    dem = None

    print("Finished!")
    print(f"Saved to: {saved_path}")


if __name__ == "__main__":
    main()
