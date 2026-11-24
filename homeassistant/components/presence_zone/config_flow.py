"""Config flow for the Presence Zones integration."""

from typing import Any, override

import probatio

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_DEVICE, CONF_ENTITIES, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import (
    entity_registry as er,
    floor_registry as fr,
    selector,
)

from .const import DOMAIN, SUBENTRY_SENSOR, SUBENTRY_ZONE

STEP_USER_SCHEMA = probatio.Schema(
    {probatio.Optional("floor"): selector.FloorSelector()}
)


class PresenceZoneConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config or options flow for Presence Zones."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user step of main integration."""
        if user_input is not None:
            floor_id = user_input["floor"] or "default"
            # one configuration per floor
            await self.async_set_unique_id(f"{DOMAIN}_{floor_id}")
            self._abort_if_unique_id_configured()
            floor_name = (
                fr.async_get(self.hass).async_get_floor(floor_id).name or floor_id
            )

            return self.async_create_entry(
                title=f"Presence Zones - {floor_name}", data={"floor_id": floor_id}
            )
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
        )

    @classmethod
    @callback
    @override
    def async_get_supported_subentry_types(
        cls, config_entry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentry flows."""
        return {SUBENTRY_ZONE: ZoneSubEntryFlow, SUBENTRY_SENSOR: SensorSubEntryFlow}


STEP_ZONE_USER_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_NAME): str,
        probatio.Required("polygon"): selector.ObjectSelector(),
    }
)


class ZoneSubEntryFlow(ConfigSubentryFlow):
    """Handle config flow for zone sub entry."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Start user step config flow."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # should change this to ID, either random or user selected
            # await self.async_set_unique_id(user_input[CONF_NAME])
            # self._abort_if_unique_id_configured()
            validated_polygon = self._validate_polygon(user_input["polygon"])
            if validated_polygon is not None:
                errors["polygon"] = validated_polygon
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data={"polygon": user_input["polygon"]}
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_ZONE_USER_SCHEMA, errors=errors
        )

    def _validate_polygon(self, polygon_input: list[list[float]]) -> str | None:
        if len(polygon_input) < 3:
            return "error_polygon_3_points"
        return None


STEP_SENSOR_USER_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_NAME): str,
        probatio.Required(CONF_DEVICE): selector.DeviceSelector(
            selector.DeviceSelectorConfig(
                entity=selector.EntityFilterSelectorConfig(
                    domain="sensor",
                    device_class="distance",
                ),
            )
        ),
        probatio.Required("sensor_position_x"): float,
        probatio.Required("sensor_position_y"): float,
        probatio.Required("sensor_position_angle", default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-180,
                max=180,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="°",
            )
        ),
    }
)


class SensorSubEntryFlow(ConfigSubentryFlow):
    """Handle config flow for sensor sub entry."""

    _name: str
    _device_id: str
    _position: list[float]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Start user step config flow."""
        if user_input is not None:
            # no ID, if user wants to use device twice he can
            self._name = user_input[CONF_NAME]
            self._device_id = user_input[CONF_DEVICE]
            self._position = [
                user_input["sensor_position_x"],
                user_input["sensor_position_y"],
                user_input["sensor_position_angle"],
            ]
            return await self.async_step_entities()

        return self.async_show_form(step_id="user", data_schema=STEP_SENSOR_USER_SCHEMA)

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Pick the distance entities belonging to the chosen device."""
        errors: dict[str, str] = {}
        if user_input is not None:
            validated_entities = self._verify_entities(user_input[CONF_ENTITIES])
            if validated_entities is not None:
                errors[CONF_ENTITIES] = validated_entities
            else:
                return self.async_create_entry(
                    title=self._name,
                    data={
                        "position": self._position,
                        "entities": user_input[CONF_ENTITIES],
                    },
                )

        device_entities = [
            entry.entity_id
            for entry in er.async_entries_for_device(
                er.async_get(self.hass), self._device_id
            )
            if entry.domain == "sensor"
        ]
        schema = probatio.Schema(
            {
                probatio.Required(CONF_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        include_entities=device_entities,
                        device_class="distance",
                        multiple=True,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="entities", data_schema=schema, errors=errors
        )

    def _verify_entities(self, entities: list[str]) -> str | None:
        # selector is already enforcing at least one entity
        if len(entities) % 2 != 0:
            return "error_even_number_xy_pair"
        return None
