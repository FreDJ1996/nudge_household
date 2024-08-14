# Nudge Household

[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]

[![Community Forum][forum-shield]][forum]

_Integration to integrate with [nudge_household][nudge_household]._

**This integration will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Show info from Budgets, Autarky Goal and Ranking
`number` | Used for Scores,Streaks and Total Score .

## Content
This integration is used to set budgets for electricity, water and gas in a household. A target for self-sufficiency can also be set. The sensors are automatically read from the Energy Dashboard. In addition to the budget, a reduction target can be set, which sets the budget each year based on last year's consumption, reduced by the reduction target.

## Frontend
The Custom [Bar Card](https://github.com/custom-cards/bar-card) or the Integrated [Gauge](https://www.home-assistant.io/dashboards/gauge/) are recommended for displaying the budget and the target. The integrated [Tile](https://www.home-assistant.io/dashboards/tile/) card is suitable for displaying the scores. If the sensors are to be tracked in detail, the Custom [History Explorer](https://github.com/SpangleLabs/history-explorer-card) Card is recommended.


## HACS Installation

1. install the [HACS](https://hacs.xyz) store as described.
1. add the link of this repository via Menu->Custom Repositories.
1. search for the Nude Household in the HACS interface
1. install the Nudge Household via the interface

## Manual Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `nudge_household`.
1. Download _all_ the files from the `custom_components/nudge_household/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Nudge Household"

## Configuration is done in the UI

1.Go to the Integration page and follow th UI Config Flow.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[nudge_household]: https://github.com/FreDj1996/nudge_household
[commits-shield]: https://img.shields.io/github/commit-activity/y/FreDj1996/nudge_household.svg?style=for-the-badge
[commits]: https://github.com/FreDj1996/nudge_household/commits/main
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/FreDj1996/nudge_household.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Frederik%20Jobst%20%40FreDj1996-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/FreDj1996/nudge_household.svg?style=for-the-badge
[releases]: https://github.com/FreDj1996/nudge_household/releases
