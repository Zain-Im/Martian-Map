
import heapq
import math
import logging
from itertools import count
from collections import OrderedDict
from pathlib import Path

import numpy as np
from osgeo import gdal

gdal.UseExceptions()
logger = logging.getLogger("martian_map.pathfinder")


class Pathfinder:

    def __init__(self, raster_path, alpha=1, heuristic_weight = 1.25, cache_blocks=64, max_escape_distance=100):

        self.raster_path = Path(raster_path)
        self.alpha = alpha
        self.heuristic_weight = heuristic_weight

        self.cache_blocks = cache_blocks
        self.max_escape_distance = max_escape_distance

        self.dataset = gdal.Open(
            str(self.raster_path),
            gdal.GA_ReadOnly
        )

        if self.dataset is None:
            raise FileNotFoundError(
                f"Could not open traversability raster: {self.raster_path}"
            )

        self.band = self.dataset.GetRasterBand(1)

        self.width = self.dataset.RasterXSize
        self.height = self.dataset.RasterYSize

        self.geotransform = self.dataset.GetGeoTransform()

        self.nodata = self.band.GetNoDataValue()

        self.block_width, self.block_height = self.band.GetBlockSize()

        self.block_cache = OrderedDict()
        self.cache_hits = self.cache_misses = 0

        # Calculate the inverse geotransform.
        gt = self.geotransform
        self.movement_distances = {
            (dx, dy): math.hypot(dx * gt[1] + dy * gt[2], dx * gt[4] + dy * gt[5])
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0),
                           (-1, -1), (1, -1), (-1, 1), (1, 1))
        }

        determinant = gt[1] * gt[5] - gt[2] * gt[4]

        if determinant == 0:
            raise ValueError("Invalid raster geotransform")

        self.inverse_determinant = 1.0 / determinant

    def close(self):
        logger.info("Raster cache: %d hits, %d misses; limit %d blocks (%d x %d)",
                    self.cache_hits, self.cache_misses, self.cache_blocks,
                    self.block_width, self.block_height)
        self.band = None
        self.dataset = None
        self.block_cache.clear()

    def get_pixel(self, x, y):

        gt = self.geotransform

        dx = x - gt[0]
        dy = y - gt[3]

        column = int(
            (dx * gt[5] - dy * gt[2])
            * self.inverse_determinant
        )

        row = int(
            (dy * gt[1] - dx * gt[4])
            * self.inverse_determinant
        )

        return column, row

    def get_map_coordinates(self, column, row):

        return (
            self.geotransform[0]
            + (column + 0.5) * self.geotransform[1]
            + (row + 0.5) * self.geotransform[2],

            self.geotransform[3]
            + (column + 0.5) * self.geotransform[4]
            + (row + 0.5) * self.geotransform[5]
        )

    def get_traversability(self, column, row):

        # Check raster boundaries.
        if (
            column < 0 or column >= self.width
            or row < 0 or row >= self.height
        ):
            return None

        # Find the block containing this pixel.
        block_x = column // self.block_width
        block_y = row // self.block_height

        block_key = (block_x, block_y)

        # Read the block if it is not cached.
        if block_key not in self.block_cache:
            self.cache_misses += 1

            x_offset = block_x * self.block_width
            y_offset = block_y * self.block_height

            x_size = min(
                self.block_width,
                self.width - x_offset
            )

            y_size = min(
                self.block_height,
                self.height - y_offset
            )

            data = self.band.ReadAsArray(
                x_offset,
                y_offset,
                x_size,
                y_size
            )

            valid = np.isfinite(data) & (data >= 0) & (data < 1)
            if self.nodata is not None:
                valid &= data != self.nodata
            self.block_cache[block_key] = (data, valid)

            # Keep the cache within its configured size.
            if len(self.block_cache) > self.cache_blocks:
                self.block_cache.popitem(last=False)

        else:
            self.cache_hits += 1
            # Move recently used blocks to the end.
            self.block_cache.move_to_end(block_key)

        data, valid = self.block_cache[block_key]

        local_x = column % self.block_width
        local_y = row % self.block_height

        return float(data[local_y, local_x]) if valid[local_y, local_x] else None

    def get_distance(self, first, second):

        first_x, first_y = self.get_map_coordinates(
            first[0], first[1]
        )

        second_x, second_y = self.get_map_coordinates(
            second[0], second[1]
        )

        return math.hypot(
            second_x - first_x,
            second_y - first_y
        )
    def find_escape_path(self, start, goal):

        x, y = start
        goal_x, goal_y = goal

        dx = abs(goal_x - x)
        dy = abs(goal_y - y)

        sx = 1 if x < goal_x else -1
        sy = 1 if y < goal_y else -1

        error = dx - dy

        escape_path = [start]
        steps = 0

        # Check whether the astronaut is already on passable terrain.
        if self.get_traversability(x, y) is not None:
            return escape_path

        while steps < self.max_escape_distance:

            if x == goal_x and y == goal_y:
                break

            error_twice = 2 * error

            if error_twice > -dy:
                error -= dy
                x += sx

            if error_twice < dx:
                error += dx
                y += sy

            escape_path.append((x, y))
            steps += 1

            # Stop when passable terrain is reached.
            if self.get_traversability(x, y) is not None:
                return escape_path

        return None
    
    def heuristic(self, current, goal):

        dx = abs(current[0] - goal[0])
        dy = abs(current[1] - goal[1])

        diagonal = min(dx, dy)
        straight = max(dx, dy) - diagonal

        return diagonal * math.sqrt(2) + straight
    
    def find_path(self, start_x, start_y, goal_x, goal_y):

        start = self.get_pixel(start_x, start_y)
        goal = self.get_pixel(goal_x, goal_y)

        start_cost = self.get_traversability(*start)
        goal_cost = self.get_traversability(*goal)

        if goal_cost is None:
            raise ValueError("Destination waypoint is impassable")

        # Find an escape path if the astronaut starts in impassable terrain.
        escape_path = [start]

        if start_cost is None:

            escape_path = self.find_escape_path(start, goal)

            if escape_path is None:
                raise ValueError(
                    "No passable terrain found within escape distance"
                )

            # Start A* from the first passable pixel.
            start = escape_path[-1]

        open_set = []

        tie_breaker = count()

        heapq.heappush(
            open_set,
            (self.heuristic(start, goal), 0.0, next(tie_breaker), start)
        )

        came_from = {}

        g_score = {start: 0.0}

        visited = set()
        self.expanded_nodes = 0
        while open_set:

            current_f, negative_g, _, current = heapq.heappop(open_set)
            current_g = -negative_g

            if current_g > g_score.get(current, float("inf")):
                continue

            if current in visited:
                continue

            if current == goal:

                path = self.reconstruct_path(came_from, current)

                # Add the escape path to the beginning of the A* path.
                if len(escape_path) > 1:

                    escape_coordinates = [
                        self.get_map_coordinates(column, row)
                        for column, row in escape_path[:-1]
                    ]

                    path = escape_coordinates + path

                return path
            self.expanded_nodes += 1

            if self.expanded_nodes % 100000 == 0:
                print(f"Expanded {self.expanded_nodes:,} nodes...", flush=True)
            visited.add(current)

            current_cost = self.get_traversability(*current)
            neighbor_costs = {
                (dx, dy): self.get_traversability(current[0] + dx, current[1] + dy)
                for dx, dy in self.movement_distances
            }

            for (dx, dy), distance in self.movement_distances.items():

                neighbor = (
                    current[0] + dx,
                    current[1] + dy
                )

                neighbor_cost = neighbor_costs[dx, dy]

                if neighbor_cost is None:
                    continue
                # Prevent diagonal movement through blocked corners.
                if dx != 0 and dy != 0:

                    horizontal = neighbor_costs[dx, 0]
                    vertical = neighbor_costs[0, dy]

                    if horizontal is None or vertical is None:
                        continue

                # Penalize movement through difficult terrain.
                terrain_multiplier = 1 + self.alpha * (
                    (current_cost + neighbor_cost) / 2
                )

                movement_cost = distance * terrain_multiplier

                tentative_g = g_score[current] + movement_cost

                if tentative_g < g_score.get(neighbor, float("inf")):

                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g

                    f_score = (
                        tentative_g
                        + self.heuristic_weight * self.heuristic(neighbor, goal)
                    )

                    heapq.heappush(
                        open_set,
                        (f_score, -tentative_g, next(tie_breaker), neighbor)
                    )

        return None

    def reconstruct_path(self, came_from, current):

        path = [current]

        while current in came_from:

            current = came_from[current]
            path.append(current)

        path.reverse()

        # Convert raster pixels into map coordinates.
        return [
            self.get_map_coordinates(column, row)
            for column, row in path
        ]
