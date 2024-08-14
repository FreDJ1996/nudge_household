from typing import Any
import homeassistant.components.energy.data as energydata
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.sensor.const import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
)
from homeassistant.components.energy import (
    is_configured as energy_dashboard_is_configured,
)
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv
from custom_components.nudge_household.platform import (
    NudgeType,
)
from homeassistant.core import callback

from .const import (
    CONF_AUTARKY_GOAL,
    CONF_BUDGET_ELECTRICITY_REDUCTION_GOAL,
    CONF_HEAT_OPTIONS,
    CONF_HEAT_SOURCE,
    CONF_HEAT_PUMP,
    CONF_APARTMENT_SIZE,
    CONF_E_Charger,
    CONF_LAST_YEAR_CONSUMED,
    CONF_NAME_HOUSEHOLD,
    CONF_SIZE_HOUSEHOLD,
    CONF_TITLE,
    DOMAIN_NUDGE_HOUSEHOLD,
    CONF_BUDGET_YEARLY_ELECTRICITY,
    CONF_BUDGET_YEARLY_HEAT,
    NudgeType,
    STEP_IDS,
    CONF_ENERGIE_EFFICIENCY,
    CONF_BUDGET_HEAT_REDUCTION_GOAL,
    CONF_AUTARKY_GOAL_INCREASE,
    CONF_BUDGET_WATER_REDUCTION_GOAL,
    CONF_BUDGET_YEARLY_WATER
)
from homeassistant.data_entry_flow import FlowResult

DATA_SCHEMAS = {
    NudgeType.ELECTRICITY_BUDGET: vol.Schema(
        {
            vol.Required(CONF_BUDGET_YEARLY_ELECTRICITY): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1000,
                    max=10000,
                    step=100,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="kWh",
                )
            ),
            vol.Required(
                CONF_BUDGET_ELECTRICITY_REDUCTION_GOAL
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=50,
                    step=1,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="%",
                )
            ),
        }
    ),
    NudgeType.HEAT_BUDGET: vol.Schema(
        {
            vol.Required(CONF_BUDGET_YEARLY_HEAT): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1000,
                    max=10000,
                    step=100,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="kWh",
                )
            ),
            vol.Required(CONF_BUDGET_HEAT_REDUCTION_GOAL): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=50,
                    step=1,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="%",
                )
            ),
        }
    ),
    NudgeType.AUTARKY_GOAL: vol.Schema(
        {
            vol.Required(CONF_AUTARKY_GOAL): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=100,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="%",
                )
            ),
            vol.Required(CONF_AUTARKY_GOAL_INCREASE): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=50,
                    step=1,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="%",
                )
            ),
        }
    ),
    NudgeType.WATER_BUDGET: vol.Schema(
        {
            vol.Required(CONF_BUDGET_YEARLY_WATER): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1000,
                    max=10000,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="liter",
                )
            ),
            vol.Required(CONF_BUDGET_WATER_REDUCTION_GOAL): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=50,
                    step=1,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="%",
                )
            ),
        }
    ),
}

SCHEMA_HEAT_PUMP = vol.Schema(
    {
        vol.Required(CONF_HEAT_PUMP): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=SENSOR_DOMAIN,
                multiple=False,
                filter=selector.EntityFilterSelectorConfig(
                    device_class=SensorDeviceClass.ENERGY
                ),
            )
        )
    }
)

SCHMEMA_HOUSEHOLD_INFOS = vol.Schema(
    {
        vol.Required(CONF_NAME_HOUSEHOLD): cv.string,
        vol.Optional(CONF_SIZE_HOUSEHOLD): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_ENERGIE_EFFICIENCY): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=250,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="kWh/(m²a)",
            )
        ),
        vol.Optional(CONF_APARTMENT_SIZE): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=10,
                max=300,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="m²",
            )
        ),
        vol.Required(CONF_HEAT_SOURCE): selector.SelectSelector(
            selector.SelectSelectorConfig(options=CONF_HEAT_OPTIONS)
        ),
        vol.Optional(CONF_E_Charger): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=SENSOR_DOMAIN,
                multiple=False,
                filter=selector.EntityFilterSelectorConfig(
                    device_class=SensorDeviceClass.ENERGY
                ),
            )
        ),
    }
)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required("test"): bool}),
        )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN_NUDGE_HOUSEHOLD):
    """Example config flow."""

    VERSION = 1
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes

    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self) -> None:
        self.data = {}
        self.nudge_support = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def validate_input(self, user_input) -> dict[NudgeType, bool]:
        nudge_support = {nudge_type: False for nudge_type in NudgeType}

        energy_manager = await energydata.async_get_manager(self.hass)

        energy_manager_data: energydata.EnergyPreferences | None = energy_manager.data

        if energy_manager_data is not None:
            energy_sources: list[energydata.SourceType] = energy_manager_data[
                "energy_sources"
            ]
        heat_pump = nudge_support[NudgeType.HEAT_BUDGET] = (
            user_input[CONF_HEAT_SOURCE] == CONF_HEAT_OPTIONS[1]
        )
        if heat_pump:
            # Create a new schema by merging the original and the heat pump schema
            heat_budget_schema = vol.Schema(
                {
                    **DATA_SCHEMAS[
                        NudgeType.HEAT_BUDGET
                    ].schema,  # Get the underlying schema dictionary
                    **SCHEMA_HEAT_PUMP.schema,  # Add the heat pump fields
                }
            )
            # Update the global DATA_SCHEMAS dictionary
            DATA_SCHEMAS[NudgeType.HEAT_BUDGET] = heat_budget_schema

        for source in energy_sources:
            if source["type"] == "grid":
                nudge_support[NudgeType.ELECTRICITY_BUDGET] = True
            elif source["type"] == "gas":
                nudge_support[NudgeType.HEAT_BUDGET] = True
            elif source["type"] == "solar":
                nudge_support[NudgeType.AUTARKY_GOAL] = True
            elif source["type"] == "water":
                nudge_support[NudgeType.WATER_BUDGET] = True
        return nudge_support

    async def async_step_user(self, user_input=None):
        if not await energy_dashboard_is_configured(self.hass):
            return self.async_abort(reason="Energy dashboard not configured")
        if user_input is not None:
            self.data = user_input
            self.nudge_support = await self.validate_input(user_input=user_input)
            for nudge_type, is_configured in self.nudge_support.items():
                if is_configured:
                    self.nudge_support[nudge_type] = False
                    return self.async_show_form(
                        step_id=STEP_IDS[nudge_type],
                        data_schema=DATA_SCHEMAS[nudge_type],
                    )

            return self.async_create_entry(title=CONF_TITLE, data=self.data)

        return self.async_show_form(step_id="user", data_schema=SCHMEMA_HOUSEHOLD_INFOS)

    async def async_step_electricity(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.data.update(user_input)
            for nudge_type, is_configured in self.nudge_support.items():
                if is_configured:
                    self.nudge_support[nudge_type] = False
                    return self.async_show_form(
                        step_id=STEP_IDS[nudge_type],
                        data_schema=DATA_SCHEMAS[nudge_type],
                    )
            return self.async_create_entry(title=CONF_TITLE, data=self.data)

        return self.async_show_form(
            step_id=STEP_IDS[NudgeType.ELECTRICITY_BUDGET],
            data_schema=DATA_SCHEMAS[NudgeType.ELECTRICITY_BUDGET],
            errors=errors,
        )

    async def async_step_heat(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.data.update(user_input)
            for nudge_type, is_configured in self.nudge_support.items():
                if is_configured:
                    self.nudge_support[nudge_type] = False
                    return self.async_show_form(
                        step_id=STEP_IDS[nudge_type],
                        data_schema=DATA_SCHEMAS[nudge_type],
                    )
            return self.async_create_entry(title=CONF_TITLE, data=self.data)

        return self.async_show_form(
            step_id=STEP_IDS[NudgeType.HEAT_BUDGET],
            data_schema=DATA_SCHEMAS[NudgeType.HEAT_BUDGET],
            errors=errors,
        )

    async def async_step_autarky(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.data.update(user_input)
            for nudge_type, is_configured in self.nudge_support.items():
                if is_configured:
                    self.nudge_support[nudge_type] = False
                    return self.async_show_form(
                        step_id=STEP_IDS[nudge_type],
                        data_schema=SCHMEMA_HOUSEHOLD_INFOS,
                    )
            return self.async_create_entry(title=CONF_TITLE, data=self.data)

        return self.async_show_form(
            step_id=STEP_IDS[NudgeType.AUTARKY_GOAL],
            data_schema=DATA_SCHEMAS[NudgeType.AUTARKY_GOAL],
            errors=errors,
        )

    async def async_step_water(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.data.update(user_input)
            for nudge_type, is_configured in self.nudge_support.items():
                if is_configured:
                    self.nudge_support[nudge_type] = False
                    return self.async_show_form(
                        step_id=STEP_IDS[nudge_type],
                        data_schema=DATA_SCHEMAS[nudge_type],
                    )
            return self.async_create_entry(title=CONF_TITLE, data=self.data)

        return self.async_show_form(
            step_id=STEP_IDS[NudgeType.HEAT_BUDGET],
            data_schema=DATA_SCHEMAS[NudgeType.HEAT_BUDGET],
            errors=errors,
        )
