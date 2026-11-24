from math import cos, sin

from homeassistant.components.presence_zone.models import Point2D, SensorViewPoint


def async_sensor_coords_to_absolute(
    sensor_position: SensorViewPoint, measured_position: Point2D
) -> Point2D:
    angle = sensor_position.angle
    absolute_x = (
        sensor_position.x
        + measured_position.x * cos(angle)
        - measured_position.y * sin(angle)
    )
    absolute_y = (
        sensor_position.y
        + measured_position.x * sin(angle)
        + measured_position.y * cos(angle)
    )

    return Point2D(x=absolute_x, y=absolute_y)


def async_is_point_in_polygon(polygon: list[Point2D], point: Point2D):
    x, y = point.x, point.y
    inside = False
    n = len(polygon)

    for i in range(n):
        # one side of the polygon, connected from P1 to P2:
        x1, y1 = polygon[i].x, polygon[i].y
        x2, y2 = polygon[(i + 1) % n].x, polygon[(i + 1) % n].y

        # raycast into +x direction from P, check if we cross the side
        if (y1 > y) != (y2 > y):
            # x of where we cross the side
            x_cross = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_cross:
                # even amount of crossings mean outside of polygon
                inside = not inside

    return inside
