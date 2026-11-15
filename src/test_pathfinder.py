
from pathlib import Path
from pathfinder import Pathfinder


project_dir = Path(__file__).resolve().parent.parent

raster_path = (
    project_dir
    / "data"
    / "processed"
    / "traversability_map.tif"
)

# Replace these with actual coordinates from your application.
start_x = 4591416.03
start_y = 1090844.98

goal_x = 4589912.84
goal_y = 1092755.81


pathfinder = Pathfinder(raster_path)

try:
    print("Full geotransform:", pathfinder.geotransform)
    print("Raster loaded successfully.")
    print(f"Raster dimensions: {pathfinder.width} x {pathfinder.height}")
    print(f"Block size: {pathfinder.block_width} x {pathfinder.block_height}")
    print(f"Pixel size: {pathfinder.geotransform[1]}, {pathfinder.geotransform[5]}")
    print(f"Pixel size: {pathfinder.geotransform[1]}, {pathfinder.geotransform[5]}")
    print(f"Block size: {pathfinder.block_width} x {pathfinder.block_height}")

    start_pixel = pathfinder.get_pixel(start_x, start_y)
    goal_pixel = pathfinder.get_pixel(goal_x, goal_y)

    print(f"Start pixel: {start_pixel}")
    print(f"Goal pixel: {goal_pixel}")

    print("Start traversability:", pathfinder.get_traversability(*start_pixel))
    print("Goal traversability:", pathfinder.get_traversability(*goal_pixel))
    print("\nCalculating route...")

    path = pathfinder.find_path(
        start_x,
        start_y,
        goal_x,
        goal_y
    )

    if path is None:

        print("No route found.")

    else:

        print("Route found!")
        print(f"Number of points: {len(path)}")
        print(f"Starting point: {path[0]}")
        print(f"Ending point: {path[-1]}")

except Exception as error:

    print(f"Pathfinding error: {error}")

finally:

    pathfinder.close()
