
import logging
logger = logging.getLogger("martian_map.map_processing")


from osgeo import gdal
from pathlib import Path
from time import perf_counter
import numpy as np
from scipy import ndimage

gdal.UseExceptions()


class Traversability:

    def __init__(
        self,
        input_path=None,
        output_path=None,
        slope_weight=0.6,
        roughness_weight=0.4,
        slope_limit=20,
        roughness_limit=0,
        nodata=-9999.0,
        block_size=512,
        elevation_unit_metres=1.0
    ):
        project_dir = Path(__file__).resolve().parent.parent

        self.input_path = input_path or project_dir / "data" / "raw" / "elevation_map.tif"
        self.output_path = output_path or project_dir / "data" / "processed" / "traversability_map.tif"
        
        self.slope_weight = slope_weight
        self.roughness_weight = roughness_weight
        self.slope_limit = slope_limit
        self.roughness_limit = roughness_limit
        self.nodata = nodata
        self.block_size = block_size
        self.elevation_unit_metres = elevation_unit_metres
        self._processing_started = None

    def log(self, message):
        """Print elapsed wall time, flushing immediately for terminal visibility."""
        if self._processing_started is None:
            self._processing_started = perf_counter()
        elapsed = perf_counter() - self._processing_started
        logger.info("[processing +%.2fs] %s", elapsed, message)

    def validate_settings(self):
        settings = (
            ("SLOPE_LIMIT", self.slope_limit),
            ("ROUGHNESS_LIMIT", self.roughness_limit),
            ("SLOPE_WEIGHT", self.slope_weight),
            ("ROUGHNESS_WEIGHT", self.roughness_weight)
        )

        for name, value in settings:
            if not np.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")

        if not np.isclose(self.slope_weight + self.roughness_weight, 1.0):
            raise ValueError("Weights must add to 1")

        if not isinstance(self.block_size, int) or self.block_size <= 0:
            raise ValueError("BLOCK_SIZE must be a positive integer")

        if (not np.isfinite(self.elevation_unit_metres)
                or self.elevation_unit_metres <= 0):
            raise ValueError("ELEVATION_UNIT_METRES must be finite and positive")

    def calculate_terrain(self, dem):
        """Generate slope and roughness rasters in memory."""
        self.log("Validating DEM geometry and units...")

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

        self.log("Calculating slope...")
        slope = gdal.DEMProcessing(
            "",
            dem,
            "slope",
            format="MEM",
            scale=srs.GetLinearUnits() / self.elevation_unit_metres
        )

        self.log("Slope calculation finished. Calculating roughness...")
        roughness = gdal.DEMProcessing(
            "",
            dem,
            "roughness",
            format="MEM"
        )

        if slope is None or roughness is None:
            raise RuntimeError("GDAL could not calculate terrain derivatives")

        self.log("Terrain derivatives finished.")
        return slope, roughness

    @staticmethod
    def normalize(array, maximum):
        """Normalize values to [0, 1]."""

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

    def calculate_cost(
        self,
        slope_array,
        roughness_array,
        slope_limit=None,
        roughness_limit=None
    ):
        """Calculate weighted terrain difficulty."""

        if np.shape(slope_array) != np.shape(roughness_array):
            raise ValueError("Slope and roughness arrays must have matching shapes")

        slope_array = np.asarray(slope_array)
        roughness_array = np.asarray(roughness_array)

        if slope_limit is None:
            slope_limit = self.slope_limit

        if roughness_limit is None:
            roughness_limit = self.roughness_limit

        slope_normalized = self.normalize(slope_array, slope_limit)
        roughness_normalized = self.normalize(roughness_array, roughness_limit)

        if slope_limit == 0 and slope_array.size:
            slope_limit = np.max(slope_array)

        if roughness_limit == 0 and roughness_array.size:
            roughness_limit = np.max(roughness_array)

        cost = (
            self.slope_weight * slope_normalized
            + self.roughness_weight * roughness_normalized
        )

        exceeds_limit = (
            (slope_array > slope_limit)
            | (roughness_array > roughness_limit)
        )

        return np.where(exceeds_limit, 1.0, cost)

    def terrain_blocks(self, slope, roughness):
        """Yield aligned arrays and their shared valid-data mask."""

        bands = [
            slope.GetRasterBand(1),
            roughness.GetRasterBand(1)
        ]

        for y in range(0, slope.RasterYSize, self.block_size):
            for x in range(0, slope.RasterXSize, self.block_size):

                w = min(self.block_size, slope.RasterXSize - x)
                h = min(self.block_size, slope.RasterYSize - y)

                arrays = [
                    band.ReadAsArray(x, y, w, h)
                    for band in bands
                ]

                if any(array is None for array in arrays):
                    raise RuntimeError(f"Could not read raster block at {x}, {y}")

                valid = np.ones((h, w), dtype=bool)

                for band, array in zip(bands, arrays):
                    valid &= np.isfinite(array) & (array >= 0)

                    nodata = band.GetNoDataValue()

                    if nodata is not None:
                        valid &= array != nodata

                    valid &= band.GetMaskBand().ReadAsArray(
                        x, y, w, h
                    ) != 0

                yield x, y, arrays[0], arrays[1], valid

    def create_traversability(self, slope, roughness, output_path):
        """Create the final traversability raster."""

        self.validate_settings()

        if (
            slope.RasterXSize,
            slope.RasterYSize,
            slope.GetGeoTransform(),
            slope.GetProjection()
        ) != (
            roughness.RasterXSize,
            roughness.RasterYSize,
            roughness.GetGeoTransform(),
            roughness.GetProjection()
        ):
            raise ValueError("Slope and roughness rasters must use the same grid and CRS")

        # Resolve automatic limits once over the entire map.
        self.log("Scanning terrain for valid pixels and map-wide normalization limits...")
        slope_limit = self.slope_limit
        roughness_limit = self.roughness_limit
        has_valid = False

        for x, y, slope_array, roughness_array, valid in self.terrain_blocks(
            slope, roughness
        ):
            if np.any(valid):
                has_valid = True

                if self.slope_limit == 0:
                    slope_limit = max(
                        slope_limit,
                        float(np.max(slope_array[valid]))
                    )

                if self.roughness_limit == 0:
                    roughness_limit = max(
                        roughness_limit,
                        float(np.max(roughness_array[valid]))
                    )

            if x + slope_array.shape[1] == slope.RasterXSize:
                rows = y + slope_array.shape[0]
                self.log(f"Limit scan: {rows}/{slope.RasterYSize} rows "
                         f"({100 * rows / slope.RasterYSize:.1f}%)")

        if not has_valid:
            raise ValueError("No valid terrain pixels to process")

        self.log(f"Normalization limits: slope={slope_limit:g}, roughness={roughness_limit:g}")
        output_path = Path(output_path)
        self.log(f"Creating output raster: {output_path}")
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

        output.SetGeoTransform(slope.GetGeoTransform())
        output.SetProjection(slope.GetProjection())

        output_band = output.GetRasterBand(1)
        output_band.SetNoDataValue(self.nodata)
        output_band.SetDescription("Terrain difficulty: 0=easiest, 1=hardest")

        output.SetMetadata({
            "SLOPE_NORMALIZATION_LIMIT": str(slope_limit),
            "ROUGHNESS_NORMALIZATION_LIMIT": str(roughness_limit),
            "SLOPE_WEIGHT": str(self.slope_weight),
            "ROUGHNESS_WEIGHT": str(self.roughness_weight)
        })

        try:
            self.log("Calculating and writing terrain difficulty blocks...")
            for x, y, slope_array, roughness_array, valid in self.terrain_blocks(
                slope, roughness
            ):
                cost = np.full(
                    slope_array.shape,
                    self.nodata,
                    dtype=np.float32
                )

                if np.any(valid):
                    cost[valid] = self.calculate_cost(
                        slope_array[valid],
                        roughness_array[valid],
                        slope_limit,
                        roughness_limit
                    )

                output_band.WriteArray(cost, x, y)
                if x + cost.shape[1] == width:
                    rows = y + cost.shape[0]
                    self.log(f"Output: {rows}/{height} rows ({100 * rows / height:.1f}%)")

            self.log("Flushing output raster to disk...")
            output.FlushCache()

        finally:
            output_band = None
            output = None

        self.log(f"Output raster saved: {output_path}")
        return output_path

    def mark_enclosed_regions(self, output_path):
        """Label non-blocked cells once with four-neighbor connectivity. Unknown
        cells participate in labeling, but any component containing one is
        protected. Thus unknown terrain can never act as a proven wall.
        """
        self.log("Finding enclosed terrain regions...")
        dataset = gdal.Open(str(output_path), gdal.GA_Update)
        band = None
        try:
            band = dataset.GetRasterBand(1)
            nodata = band.GetNoDataValue()
            width, height = dataset.RasterXSize, dataset.RasterYSize

            def blocks():
                for y in range(0, height, self.block_size):
                    for x in range(0, width, self.block_size):
                        w = min(self.block_size, width - x)
                        h = min(self.block_size, height - y)
                        values = band.ReadAsArray(x, y, w, h)
                        valid = np.isfinite(values)
                        if nodata is not None:
                            valid &= values != nodata
                        valid &= band.GetMaskBand().ReadAsArray(x, y, w, h) != 0
                        yield x, y, values, valid

            passable = np.empty((height, width), dtype=bool)
            for x, y, values, valid in blocks():
                h, w = values.shape
                passable[y:y+h, x:x+w] = ~valid | (values < 1.0)

            labels = np.empty((height, width), dtype=np.int32)
            structure = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
            count = ndimage.label(passable, structure=structure, output=labels)
            del passable
            self.log(f"Labeled {count} connected regions; checking boundaries and NoData...")

            # Direct label indexing avoids sorting or scanning once per region.
            open_region = np.zeros(count + 1, dtype=bool)
            open_region[0] = True  # Label zero is already blocked terrain.
            open_region[labels[0, :]] = True
            open_region[labels[-1, :]] = True
            open_region[labels[:, 0]] = True
            open_region[labels[:, -1]] = True
            for x, y, values, valid in blocks():
                h, w = values.shape
                local_labels = labels[y:y+h, x:x+w]
                open_region[local_labels[~valid]] = True

            enclosed_count = int(np.count_nonzero(~open_region))
            changed = 0
            for x, y, values, valid in blocks():
                h, w = values.shape
                enclosed = valid & ~open_region[labels[y:y+h, x:x+w]]
                pixels = int(np.count_nonzero(enclosed))
                if pixels:
                    values[enclosed] = 1.0
                    band.WriteArray(values, x, y)
                    changed += pixels
            dataset.SetMetadataItem("ENCLOSURE_CONNECTIVITY", "4")
            dataset.SetMetadataItem("ENCLOSED_REGIONS_FILLED", str(enclosed_count))
            dataset.SetMetadataItem("ENCLOSED_PIXELS_FILLED", str(changed))
            dataset.FlushCache()
            self.log(f"Marked {changed} cells in {enclosed_count} enclosed regions untraversable.")
            return changed
        finally:
            band = None
            dataset = None

    def generate(self):
        """Run the complete traversability generation process."""

        self._processing_started = perf_counter()
        self.log("Processing started. Validating settings...")
        self.validate_settings()

        logger.info("Terrain settings: slope_limit=%s roughness_limit=%s weights=(%s, %s) block_size=%s",
                    self.slope_limit, self.roughness_limit, self.slope_weight,
                    self.roughness_weight, self.block_size)
        self.log(f"Opening DEM: {self.input_path}")
        dem = gdal.Open(str(self.input_path))

        if dem is None:
            raise RuntimeError(f"Could not open DEM: {self.input_path}")

        try:
            self.log(f"DEM opened: {dem.RasterXSize} x {dem.RasterYSize} pixels")
            slope, roughness = self.calculate_terrain(dem)

            output_path = self.create_traversability(
                slope,
                roughness,
                self.output_path
            )

            # Release full-size derivative rasters before allocating region labels.
            slope = roughness = dem = None
            self.mark_enclosed_regions(output_path)
            self.log("Processing finished.")
            return output_path

        finally:
            dem = None
