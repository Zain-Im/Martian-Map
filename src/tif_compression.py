from osgeo import gdal
from pathlib import Path

gdal.UseExceptions()


class TifCompressor:
    """Compress GeoTIFFs to disk or decompress rasters into GDAL memory.

    The output remains a GeoTIFF even when its filename ends in .zstd.
    Existing output files are replaced; the input is never overwritten.
    """

    def __init__(self, input, output=None):
        self.input_path = Path(input)
        self.output_path = Path(output) if output is not None else None

    def compress(self):
        """Losslessly compress using ZSTD level 3; return the output Path."""
        if self.output_path is None:
            raise ValueError("An output path is required for compression")
        if not self.input_path.is_file():
            raise FileNotFoundError(f"Input raster does not exist: {self.input_path}")
        if self.input_path.resolve() == self.output_path.resolve() or (
            self.output_path.exists() and self.input_path.samefile(self.output_path)
        ):
            raise ValueError("Input and output paths must differ")

        source = gdal.Open(str(self.input_path), gdal.GA_ReadOnly)
        output = None
        try:
            if source is None or source.RasterCount == 0:
                raise ValueError(f"Input is not a raster: {self.input_path}")

            options = ["TILED=YES", "BIGTIFF=IF_SAFER", "COMPRESS=ZSTD", "ZSTD_LEVEL=3"]
            # Floating-point prediction is invalid for integer imagery.
            floating = all(
                source.GetRasterBand(index).DataType in (
                    gdal.GDT_Float32, gdal.GDT_Float64
                )
                for index in range(1, source.RasterCount + 1)
            )
            options.append("PREDICTOR=3" if floating else "PREDICTOR=1")

            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            output = gdal.Translate(
                str(self.output_path),
                source,
                format="GTiff",
                creationOptions=options,
            )
            if output is None:
                raise RuntimeError(f"Could not create raster: {self.output_path}")
            output.FlushCache()
        finally:
            output = None
            source = None

        return self.output_path

    def decompress(self):
        """Return a GDAL MEM dataset without writing any output file.

        Keep the returned dataset alive while accessing its bands. Release it
        by setting it to None when finished. The output path is unused.
        """
        if not self.input_path.is_file():
            raise FileNotFoundError(f"Input raster does not exist: {self.input_path}")

        source = gdal.Open(str(self.input_path), gdal.GA_ReadOnly)
        try:
            if source is None or source.RasterCount == 0:
                raise ValueError(f"Input is not a raster: {self.input_path}")
            output = gdal.Translate("", source, format="MEM")
            if output is None:
                raise RuntimeError(f"Could not decompress raster: {self.input_path}")
            return output
        finally:
            source = None
