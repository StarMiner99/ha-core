from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.presence_zone.models import Point2D, SensorConfig
from homeassistant.components.presence_zone.zone_calculator import (
    async_is_point_in_polygon,
    async_sensor_coords_to_absolute,
)
from homeassistant.config_entries import _LOGGER
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.util import Callable

if TYPE_CHECKING:
    from homeassistant.components.presence_zone.binary_sensor import (
        PresenceZoneMotionSensorEntity,
    )

type MotionSensorCallback = tuple[
    PresenceZoneMotionSensorEntity, Callable[[bool, str], None]
]


class PresenceEntityUpdater:
    _input_sensors: list[SensorConfig]

    def __init__(self, input_sensors: list[SensorConfig], hass: HomeAssistant) -> None:
        self._input_sensors = input_sensors
        self._output_presence_entities: list[MotionSensorCallback] = []
        self._hass = hass

    def register_entity(
        self,
        entity: PresenceZoneMotionSensorEntity,
        callback_fn: Callable[[bool, str], None],
    ) -> None:
        self._output_presence_entities.append((entity, callback_fn))

    def _async_get_float_from_state(self, entity_id: str) -> float | None:
        state = self._hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            return float(state.state)
        except ValueError:
            return None

    @callback
    def async_input_sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        _LOGGER.warning(event)
        for sensor in self._input_sensors:
            if sensor.contains_entity_id(event.data["entity_id"]):
                points: list[Point2D] = []
                # check all sensor x/y pairs
                for x_entity_id, y_entity_id in sensor.entity_ids:
                    coordinate_x = self._async_get_float_from_state(x_entity_id)
                    coordinate_y = self._async_get_float_from_state(y_entity_id)
                    _LOGGER.warning("coord: %f, %f", coordinate_x, coordinate_y)
                    if (
                        coordinate_x is None  # at least one coordinate is missing
                        or coordinate_y is None
                        or (
                            coordinate_x == 0 and coordinate_y == 0
                        )  # if the sensor reports 0,0 it is most likely a poorly made "no target" state
                    ):
                        continue
                    coordinate_measured = Point2D(coordinate_x, coordinate_y)
                    coordinate_absolute = async_sensor_coords_to_absolute(
                        sensor.position, coordinate_measured
                    )
                    points.append(coordinate_absolute)
                self._async_check_zones(points, sensor.uuid)

    def _async_check_zones(
        self, points: list[Point2D], triggered_sensor_uid: str
    ) -> None:
        for motion_sensor, motion_callback in self._output_presence_entities:
            polygon = motion_sensor.async_get_polygon()
            callback_triggered = False
            for point in points:
                if async_is_point_in_polygon(polygon, point):
                    callback_triggered = True
                    motion_callback(True, triggered_sensor_uid)
                    break
            if not callback_triggered and motion_sensor.async_is_currently_triggered_by(
                triggered_sensor_uid
            ):
                motion_callback(False, triggered_sensor_uid)
