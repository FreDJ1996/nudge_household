"""
Custom integration to integrate nudge_apps with Home Assistant.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .const import MyConfigEntry, MyData

PLATFORMS: list[Platform] = [Platform.NUMBER, Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MyConfigEntry,
) -> bool:
    entry.runtime_data = MyData(score_device_unique_ids={})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
