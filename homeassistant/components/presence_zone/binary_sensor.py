"""Binary sensor platform for Presence Zones integration."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.presence_zone.entity_updater import PresenceEntityUpdater
from homeassistant.components.presence_zone.models import (
    Point2D,
    flatten_sensor_config_to_entity_ids,
    parse_sensor_configs,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import SUBENTRY_SENSOR, SUBENTRY_ZONE


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize Presence Zones config entry."""

    sensors_raw = config_entry.get_subentries_of_type(SUBENTRY_SENSOR)
    sensors = parse_sensor_configs(sensors_raw)
    sensor_entity_ids = flatten_sensor_config_to_entity_ids(sensors)
    updater = PresenceEntityUpdater(sensors, hass)

    config_entry.async_on_unload(
        async_track_state_change_event(
            hass, sensor_entity_ids, updater.async_input_sensor_changed
        )
    )

    zones = config_entry.get_subentries_of_type(SUBENTRY_ZONE)

    async_add_entities(
        [
            PresenceZoneMotionSensorEntity(
                zone.unique_id, zone.title, zone.data["polygon"], updater
            )
            for zone in zones
        ]
    )


class PresenceZoneMotionSensorEntity(BinarySensorEntity):
    """Presence zone binary sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "presence_zone_motion"

    _attr_should_poll = False

    def __init__(
        self,
        unique_id: str,
        zone_name: str,
        polygon: list[list[float]],
        updater: PresenceEntityUpdater,
    ) -> None:
        """Initialize binary sensor."""
        super().__init__()
        self._attr_unique_id = unique_id
        self._attr_translation_placeholders = {"zone_name": zone_name}
        self._polygon_points = [Point2D(x=point[0], y=point[1]) for point in polygon]
        self._updater = updater
        # list of sensors unique ids which triggered motion in this zone
        self._activated_by: set[str] = set()

    async def async_added_to_hass(self) -> None:
        """Register entity as soon as added to hass."""
        await super().async_added_to_hass()
        self._updater.register_entity(self, self._async_handle_update)

    @callback
    def _async_handle_update(self, is_on: bool, sensor_uid: str) -> None:
        """Store the new value and write it."""
        if is_on:
            self._activated_by.add(sensor_uid)
        else:
            self._activated_by.remove(sensor_uid)
        self._attr_is_on = is_on
        self.async_write_ha_state()

    def async_is_currently_triggered_by(self, sensor_uid: str) -> bool:
        return sensor_uid in self._activated_by

    def async_get_polygon(self) -> list[Point2D]:
        return self._polygon_points
