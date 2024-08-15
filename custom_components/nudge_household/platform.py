"""Plattform for building Nudge Apps."""

import logging
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Final

import homeassistant.components.energy.data as energydata
import voluptuous as vol
from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.components.number.const import NumberDeviceClass
from homeassistant.components.recorder.statistics import (
    statistics_during_period,
)
from homeassistant.components.recorder.util import get_instance
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorStateClass
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform, entity_registry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.device_registry import (
    async_get as async_get_device_registry,
)
from homeassistant.helpers.entity_registry import (
    EntityRegistry,
)
from homeassistant.helpers.entity_registry import (
    async_get as async_get_entity_registry,
)
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

CONF_CHOOSE_ACTION = "action"


CONF_NUDGE_PERSON = "username"
CONF_BUDGET_YEARLY = "budget_yearly"
CONF_TRACKED_SENSOR_ENTITIES = "sensor_entities"
SERVICE_SET_RANK_FOR_USER = "set_rank_for_user"
SERVICE_ADD_POINTS_TO_USER = "add_points_to_score"
SERVICE_UPDATE_STREAK = "update_streak"

BADGES = [
    "Sparfuchs",
    "Energiespar-Anfänger",
    "Energieeffizienz-Experte",
    "Nachhaltigkeits-Champion",
]


class NudgeType(Enum):
    """Defines the different kinds of Nudges."""

    ELECTRICITY_BUDGET = auto()
    HEAT_BUDGET = auto()
    WATER_BUDGET = auto()
    AUTARKY_GOAL = auto()
    E_MOBILITY_Budget = auto()
    CO2_BUDGET = auto()
    MONEY_BUDGET = auto()


NUDGE_ICONS = {
    NudgeType.ELECTRICITY_BUDGET: "mdi:lightning-bolt",
    NudgeType.HEAT_BUDGET: "mdi:lightning-bolt",
    NudgeType.WATER_BUDGET: "mdi:lightning-bolt",
    NudgeType.AUTARKY_GOAL: "mdi:lightning-bolt",
    NudgeType.CO2_BUDGET: "mdi:lightning-bolt",
    NudgeType.MONEY_BUDGET: "mdi:lightning-bolt",
}


class NudgePeriod(Enum):
    """Defines the Periods for the Budgets and Goals."""

    Daily = auto()
    Weekly = auto()
    Monthly = auto()
    Yearly = auto()


class EnergyElectricDevices(Enum):
    """Different kinds of Sensor Devices needed for Electricity Usage Calculation."""

    BATTERY_EXPORT = auto()
    BatteryImport = auto()
    SolarProduction = auto()
    GridExport = auto()
    GridImport = auto()
    HeatPump = auto()
    ECharger = auto()

def get_entity_from_uuid(hass:HomeAssistant, uuid:str, domain:str,
                         platform:str)-> str|None:
    """Return the entity ID for a given Unique ID."""
    er = entity_registry.async_get(hass)
    return er.async_get_entity_id(platform=domain,domain=platform,unique_id=uuid)


def get_start_time(nudge_period: NudgePeriod) -> datetime:
    """Return the start time for a given Nudge Persiod."""
    now = dt_util.now()
    if nudge_period == NudgePeriod.Daily:
        start_time = now
    if nudge_period == NudgePeriod.Weekly:
        start_time = now - timedelta(
            days=now.weekday()
        )  # Zurück zum Wochenanfang (Montag)
    elif nudge_period == NudgePeriod.Monthly:
        start_time = now
        start_time.replace(day=1)
    elif nudge_period == NudgePeriod.Yearly:
        start_time = now
        start_time.replace(day=1, month=1)

    return start_time.replace(
        hour=0, minute=0, second=0, microsecond=0
    )  # Zeit auf 00:00 Uhr setzen


async def get_energy_entities(
    hass: HomeAssistant,
) -> tuple[dict[EnergyElectricDevices, str], str | None, str | None]:
    """Return the different Entities from the Energy Manager."""
    energy_manager = await energydata.async_get_manager(hass)

    energy_manager_data: energydata.EnergyPreferences | None = energy_manager.data
    energy_entities = {}
    gas = None
    water = None
    if energy_manager_data:
        energy_sources = energy_manager_data.get("energy_sources", [])
        for source in energy_sources:
            if source["type"] == "grid":
                grid_imports = source.get("flow_from")
                for grid_import in grid_imports:
                    energy_entities[EnergyElectricDevices.GridImport] = grid_import[
                        "stat_energy_from"
                    ]
                grid_exports = source.get("flow_to")
                for grid_export in grid_exports:
                    energy_entities[EnergyElectricDevices.GridExport] = grid_export[
                        "stat_energy_to"
                    ]
            elif source["type"] == "battery":
                energy_entities[EnergyElectricDevices.BATTERY_EXPORT] = source.get(
                    "stat_energy_to"
                )
                energy_entities[EnergyElectricDevices.BatteryImport] = source.get(
                    "stat_energy_from"
                )
            elif source["type"] == "solar":
                energy_entities[EnergyElectricDevices.SolarProduction] = source.get(
                    "stat_energy_from"
                )
            elif source["type"] == "gas":
                gas = source.get("stat_energy_from")
            elif source["type"] == "water":
                water = source.get("stat_energy_from")
    return energy_entities, gas, water


async def get_long_term_statistics(
    statistic_ids: set[str], period: NudgePeriod, hass: HomeAssistant
) -> dict[str, float]:
    """Return the sum of a set of sensors from the long-term statistics."""
    statistics_period = {
        NudgePeriod.Daily: "day",
        NudgePeriod.Weekly: "week",
        NudgePeriod.Monthly: "month",
        NudgePeriod.Yearly: "month",
    }

    statistic_period = statistics_period[period]
    start_time = get_start_time(period)
    end_time = None
    units = None

    type_statistic: Final = "change"
    stats = await get_instance(hass=hass).async_add_executor_job(
        statistics_during_period,
        hass,
        start_time,
        end_time,
        statistic_ids,
        statistic_period,
        units,
        {type_statistic},
    )
    sum_budget = 0.0
    for entity in stats.values():
        for stat in entity:
            sum_value = stat.get(type_statistic)
            if sum_value is not None:
                sum_budget += sum_value
    entities_sum = {}
    for entity, values in stats.items():
        sum_entity = 0.0
        for stat in values:
            sum_value = stat.get(type_statistic)
            if sum_value is not None:
                sum_entity += sum_value
        entities_sum[entity] = sum_entity

    return entities_sum


async def get_own_total_consumtion(
    energy_entities: dict[EnergyElectricDevices, str],
    period: NudgePeriod,
    hass: HomeAssistant,
) -> tuple[float, float]:
    """Return the own consumtion and the total consumtion of the household."""
    statistic_ids = set(energy_entities.values())
    entities_energy = {value: key for key, value in energy_entities.items()}

    stats = await get_long_term_statistics(
        statistic_ids=statistic_ids, period=period, hass=hass
    )
    energy_values = {device: 0.0 for device in EnergyElectricDevices}

    for entity, value in stats.items():
        energy_values[entities_energy[entity]] += value

    # Degree of self-sufficiency (%) = (self-consumption (kWh) /
    # total consumption (kWh)) * 100

    # Self-consumption = battery export-battery import
    # + solar production - electricity export

    # Total consumption = self-consumption + electricity import
    own_consumption = (
        energy_values[EnergyElectricDevices.BATTERY_EXPORT]
        - energy_values[EnergyElectricDevices.BatteryImport]
        + energy_values[EnergyElectricDevices.SolarProduction]
        + energy_values[EnergyElectricDevices.GridExport]
    )
    total_consumption = (
        own_consumption + energy_values[EnergyElectricDevices.GridImport]
    )
    return own_consumption, total_consumption


class Nudge(SensorEntity):
    """Base Class for Budgets and Goals."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = True

    def __init__(  # noqa: D107, PLR0913
        self,
        entry_id: str,
        device_info: DeviceInfo,
        attr_name: str,
        nudge_period: NudgePeriod,
        goal: float,
        score_entity: str | None,
        nudge_type: NudgeType,
        domain: str,
    ) -> None:
        super().__init__()
        self._attr_unique_id = f"{entry_id}_{nudge_period.name}"
        self._nudge_period = nudge_period
        self._attr_name = attr_name
        self._attr_device_info = device_info
        self._goal = goal
        self._last_update = datetime.now(tz=dt_util.DEFAULT_TIME_ZONE)
        self._score_entity = score_entity
        self._goal_reached = False
        self._attr_icon = NUDGE_ICONS[nudge_type]
        self._domain = domain

    async def async_added_to_hass(self) -> None:
        """Update Points every evening."""
        if self._nudge_period == NudgePeriod.Daily:
            async_track_time_change(self.hass, self.send_points_to_user, second=59)

    @callback
    async def send_points_to_user(self, now: datetime) -> None:  # noqa: ARG002
        """Service for sending points to a score/user."""
        if not self._score_entity:
            return
        points = 1 if self._goal_reached else 0
        if points != 0:
            await self.hass.services.async_call(
                domain=self._domain,
                service=SERVICE_ADD_POINTS_TO_USER,
                service_data={"goal_reached": self._goal_reached},
                target={"entity_id": self._score_entity},
            )


class Budget(Nudge):
    """Budget for Nudging with goal and actual."""

    @staticmethod
    def calculate_goals(yearly_goal: float) -> dict[NudgePeriod, float]:
        """Return the yearly goal divided into sub goals for every Nudge Period."""
        goals = {NudgePeriod.Yearly: yearly_goal}
        goals[NudgePeriod.Daily] = yearly_goal / 365
        goals[NudgePeriod.Weekly] = goals[NudgePeriod.Daily] * 7
        goals[NudgePeriod.Monthly] = goals[NudgePeriod.Yearly] / 12
        return goals

    def __init__(  # noqa: D107, PLR0913
        self,
        entry_id: str,
        goal: float,
        attr_name: str,
        device_info: DeviceInfo,
        nudge_period: NudgePeriod,
        nudge_type: NudgeType,
        domain: str,
        reduction_goal: int,
        score_entity: str | None,
        energy_entities: dict[EnergyElectricDevices, str] | None = None,
        budget_entities: set[str] | None = None,
    ) -> None:
        super().__init__(
            entry_id=entry_id,
            device_info=device_info,
            attr_name=attr_name,
            nudge_period=nudge_period,
            goal=goal,
            score_entity=score_entity,
            nudge_type=nudge_type,
            domain=domain,
        )
        self._attr_unique_id = f"{entry_id}_{nudge_period.name}"
        self._actual = 0.0
        self._budget_entities = budget_entities
        self._energy_entities = energy_entities
        self._attr_native_value: int = 0
        self._attr_native_unit_of_measurement = "%"
        self._reduction_goal = reduction_goal

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes of the sensor."""
        attributes = {}
        attributes["last_update"] = self._last_update
        attributes["actual"] = self._actual
        attributes["goal"] = self._goal
        attributes["actual/goal"] = f"{self._actual} kWh / {self._goal} kWh"

        return attributes

    async def async_update(self) -> None:
        """Update the actual value of the budget."""
        sum_budget = 0.0
        if self._budget_entities:
            stats = await get_long_term_statistics(
                self._budget_entities, self._nudge_period, self.hass
            )
            for value in stats.values():
                sum_budget += value
        elif self._energy_entities:
            own_consumtion, total_consumtion = await get_own_total_consumtion(
                energy_entities=self._energy_entities,
                period=self._nudge_period,
                hass=self.hass,
            )
            sum_budget = own_consumtion

        self._actual = sum_budget
        self._goal_reached = self._actual < self._goal
        self._attr_native_value = round(self._actual / self._goal * 100)
        self._last_update = datetime.now(tz=dt_util.DEFAULT_TIME_ZONE)
        self.async_write_ha_state()

    @callback
    async def set_budget_with_history_data(self) -> bool:
        """Use the reduction goal for setting a new budget."""
        self._goal = int(
            ((100 * self._goal) - (self._reduction_goal * self._goal)) / 100
        )
        return True

def register_services() -> None:
    """Register services for the Rank and score system."""
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_RANK_FOR_USER,
        {
            vol.Required("ranking_position"): cv.positive_int,
            vol.Required("ranking_length"): cv.positive_int,
        },
        "set_ranking_position",
    )
    platform.async_register_entity_service(
        SERVICE_ADD_POINTS_TO_USER,
        {
            vol.Required("goal_reached"): cv.boolean,
        },
        SERVICE_ADD_POINTS_TO_USER,
    )
    platform.async_register_entity_service(
        SERVICE_UPDATE_STREAK,
        {
            vol.Required("goal_reached"): cv.boolean,
        },
        SERVICE_UPDATE_STREAK,
    )



class Streak(RestoreNumber):
    """Gamification Feature that counts the number of days with achieved nudge."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "days"

    def __init__(
        self,
        nudge_type: NudgeType,
        entry_id: str,
        device_info: DeviceInfo | None = None,
    ) -> None:
        """Set up the Streak."""
        super().__init__()
        self._attr_device_info = device_info
        self._attr_native_value: int = 0
        self.nudge_type = nudge_type
        self._attr_name = f"Streak {nudge_type.name.replace("_"," ").capitalize()}"
        self._attr_unique_id: str = f"{entry_id}_{nudge_type.name}_Streak"

    async def update_streak(self, goal_reached: bool) -> None:  # noqa: FBT001
        """Calll from Score every evenig, to tell if nudge achieved."""
        if goal_reached:
            self._attr_native_value += 1
        else:
            self._attr_native_value = 0

    def get_unique_id(self) -> str:
        """Return the unique ID of the Streak."""
        return self._attr_unique_id



class Score(RestoreNumber):
    """Nudge Person for Nudging."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "points"
    _attr_device_class = NumberDeviceClass.AQI

    def __init__(
        self,
        nudge_type: NudgeType,
        entry_id: str,
        streak: Streak,
        domain:str,
        device_info: DeviceInfo | None = None,
    ) -> None:
        """Set up Score Entity."""
        super().__init__()
        self._attr_device_info = device_info
        self.ranking_position = "0/0"
        self._attr_native_value: int = 0
        self.nudge_type = nudge_type
        self._attr_name = f"Score {nudge_type.name.replace("_"," ").capitalize()}"
        self._attr_unique_id: str = f"{entry_id}_{nudge_type.name}_Score"
        self._streak_uuid = streak.get_unique_id()
        self._streak_entity_id = None
        self._domain = domain

    async def set_ranking_position(
        self, ranking_position: int, ranking_length: int
    ) -> None:
        """Set ranking position from rank entity."""
        self.ranking_position = f"{ranking_position}/{ranking_length}"

    async def add_points_to_score(self, goal_reached: bool) -> None:  # noqa: FBT001
        """If nudge achieved, then add point to related score."""
        if goal_reached:
            self._attr_native_value += 1
        if not self._streak_entity_id:
            entity_registry = async_get_entity_registry(self.hass)
            self._streak_entity_id = entity_registry.async_get_entity_id(
                platform=self._domain, domain=Platform.NUMBER,
                unique_id=self._streak_uuid
            )

        await self.hass.services.async_call(
            domain=self._domain,
            service=SERVICE_UPDATE_STREAK,
            service_data={"goal_reached": goal_reached},
            target={"entity_id": self._streak_entity_id},
        )

    def get_unique_id(self) -> str:
        """"Return the unique id for score entity."""
        return self._attr_unique_id

    @callback
    def reset_score(self, _: datetime) -> None:
        """Reset the score to zero."""
        self._attr_native_value = 0

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes of the sensor."""
        return {"rank": self.ranking_position}

    async def async_added_to_hass(self) -> None:
        """Register cron jobs and restore last state."""
        now = datetime.now(tz=dt_util.DEFAULT_TIME_ZONE)
        new_year= now.replace(year=now.year+1,month=1,day=1,hour=0,minute=0,second=0)
        async_track_point_in_time(self.hass,self.reset_score,new_year)
        """Restore last state."""
        last_number_data = await self.async_get_last_number_data()
        if last_number_data and last_number_data.native_value:
            self._attr_native_value = int(last_number_data.native_value)
        else:
            self._attr_native_value = 0


    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        if value.is_integer():
            self._attr_native_value = int(value)
            self.async_write_ha_state()


class TotalScore(NumberEntity):
    """Combines multiple scores form different NudgeTypes to one total Score."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "points"

    def __init__(
        self,
        entity_uuids_scores: dict[NudgeType, str],
        domain: str,
        entry_id: str,
        device_info: DeviceInfo | None = None,
    ) -> None:
        """Set up total score."""
        super().__init__()
        self._attr_device_info = device_info
        self.ranking_position = "0/0"
        self._attr_native_value: int = 0
        self._entity_ids: dict[NudgeType, str] = {}
        self._entity_uuids_scores = entity_uuids_scores
        self._domain = domain
        self._attr_name = "Total Score"
        self._attr_unique_id: str = f"{entry_id}_total_score"

    @staticmethod
    def get_entity_ids_from_uuid(
        entity_registry: EntityRegistry, uuids: dict[NudgeType, str], domain: str
    ) -> dict[NudgeType, str]:
        """Return entity ids for given uuids."""
        entity_ids: dict[NudgeType, str] = {}

        for nudgetype, uuid in uuids.items():
            entity_id = entity_registry.async_get_entity_id(
                platform=domain, domain=Platform.NUMBER, unique_id=uuid
            )
            if entity_id:
                entity_ids[nudgetype] = entity_id

        return entity_ids

    async def async_added_to_hass(self) -> None:
        """Get entity ids from score unique ids."""
        entity_registry = async_get_entity_registry(self.hass)
        self._entity_ids = TotalScore.get_entity_ids_from_uuid(
            entity_registry=entity_registry,
            uuids=self._entity_uuids_scores,
            domain=self._domain,
        )

    async def async_update(self) -> None:
        """Go through the list of scores and sum up total score."""
        totalpoints: int = 0
        points_per_nudge: dict[NudgeType, int] = {}
        for nudge_type, score_entity in self._entity_ids.items():
            state = self.hass.states.get(score_entity)
            if state:
                value = int(state.state)
                totalpoints += value
                points_per_nudge[nudge_type] = value

        self._attr_native_value = totalpoints
        self._attr_extra_state_attributes = {
            nudge_type.name: score for nudge_type, score in points_per_nudge.items()
        }
        self._attr_extra_state_attributes["Total"] = self.ranking_position

        self.async_write_ha_state()

    def get_entities_for_device_info(self, device_info: DeviceInfo) -> list:
        """Get all entities for a given device_info."""
        entity_registry = async_get_entity_registry(self.hass)
        device_registry = async_get_device_registry(self.hass)
        device = None

        identifiers = device_info.get("identifiers")
        if identifiers is None:
            return []

        for dev in device_registry.devices.values():
            if any(identifier in dev.identifiers for identifier in identifiers):
                device = dev
                break

        if device is None:
            return []

        return [
            entry.entity_id
            for entry in entity_registry.entities.values()
            if entry.device_id == device.id
        ]
