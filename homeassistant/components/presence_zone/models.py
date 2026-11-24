from typing import TypedDict

from hassfest.model import dataclass

from homeassistant.config_entries import ConfigSubentry


@dataclass(frozen=True)
class SensorViewPoint:
    x: float
    y: float
    angle: float

    @classmethod
    def from_list(cls, values: list[float]) -> SensorViewPoint:
        return cls(x=values[0], y=values[1], angle=values[2])


@dataclass
class Point2D:
    x: float
    y: float


class RawSensorConfig(TypedDict):
    """Serialized shape stored in config entry data/options."""

    position: list[float]
    entities: list[str]


@dataclass(frozen=True)
class SensorConfig:
    uuid: str
    position: SensorViewPoint
    entity_ids: list[
        tuple[str, str]
    ]  # list of x,y pairs -> order that user inputs matters

    @classmethod
    def from_raw(cls, raw: RawSensorConfig, unique_id: str) -> SensorConfig:
        entities = raw["entities"]
        return cls(
            uuid=unique_id,
            position=SensorViewPoint.from_list(raw["position"]),
            entity_ids=[
                (entities[i], entities[i + 1]) for i in range(0, len(entities), 2)
            ],
        )

    def contains_entity_id(self, entity_id: str):
        return entity_id in [
            entity_id for entity_pair in self.entity_ids for entity_id in entity_pair
        ]


def parse_sensor_configs(entries: list[ConfigSubentry]) -> list[SensorConfig]:
    return [SensorConfig.from_raw(entry.data, entry.unique_id) for entry in entries]


def flatten_sensor_config_to_entity_ids(sensors: list[SensorConfig]) -> list[str]:
    return [
        entity_id
        for sensor in sensors
        for entity_pair in sensor.entity_ids
        for entity_id in entity_pair
    ]
