"""MartianMap application entry point."""
import sys
from pathlib import Path
from boot_logging import configure_logging, stage


def main():
    logger = configure_logging().getChild('startup')
    logger.info('Booting MartianMap')
    logger.info('Python %s | executable=%s', sys.version.split()[0], sys.executable)
    logger.info('Project=%s | working directory=%s', Path(__file__).resolve().parent.parent, Path.cwd())
    with stage(logger, 'Import QGIS'):
        from qgis.core import QgsApplication, QgsProject, Qgis
        from qgis.PyQt.QtCore import QTimer
        from qgis.PyQt import sip
    logger.info('QGIS %s', Qgis.QGIS_VERSION)
    with stage(logger, 'Import application and processing dependencies'):
        from app import MartianMapWindow
        from map_processing import Traversability
    # Generate traversability raster only if it doesn't already exist.
    project_dir = Path(__file__).resolve().parent.parent
    traversability_path = (
        project_dir / "data" / "processed" / "traversability_map.tif"
    )

    if traversability_path.exists():
        logger.info(
            'Traversability raster already exists: %s',
            traversability_path
        )

    else:
        traversability_path.parent.mkdir(parents=True, exist_ok=True)

        with stage(logger, 'Generate traversability raster'):
            saved_path = Traversability(
                output_path=traversability_path
            ).generate()

        logger.info('Traversability saved: %s', saved_path)
    qgs = None
    window = None
    try:
        with stage(logger, 'Initialize QGIS providers'):
            qgs = QgsApplication([], True)
            qgs.initQgis()
        logger.info('QGIS prefix=%s', QgsApplication.prefixPath())
        with stage(logger, 'Build window, load maps, and insert waypoints'):
            window = MartianMapWindow()
        window.show()
        logger.info('Window shown; starting event loop')
        QTimer.singleShot(0, lambda: logger.info('Boot complete; event loop responsive'))
        exit_code = qgs.exec()
        logger.info('Event loop stopped: exit code %s', exit_code)
        return exit_code
    finally:
        if qgs is not None:
            logger.info('Shutting down QGIS')
            if window is not None:
                window.map_canvas.stopRendering()
                window.close()
                sip.delete(window)
                window = None
            QgsProject.instance().clear()
            qgs.exitQgis()
            logger.info('Shutdown complete')


if __name__ == '__main__':
    sys.exit(main())
