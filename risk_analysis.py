from typing import Literal, TypedDict


DamageLevel = Literal["no_damage", "damaged", "collapsed"]
TimeOfDay = Literal["day", "night"]
BuildingType = Literal["residential", "office", "school", "hospital", "shopping_mall"]
OccupancyRange = Literal["auto", "low", "medium", "high"]
RiskLevel = Literal["very_low", "low", "medium", "high", "critical"]
MoneyRange = tuple[int, int]


class EconomicLossBreakdown(TypedDict):
    structural_loss: str
    debris_removal: str
    interior_loss: str


class RiskAnalysisResult(TypedDict):
    estimated_population_range: str
    estimated_casualty_range: str
    risk_level: RiskLevel
    economic_loss_range_try: str
    economic_loss_level: str
    economic_loss_breakdown: EconomicLossBreakdown


# Scenario-based population ranges. These are not exact occupancy values.
POPULATION_RANGES: dict[BuildingType, dict[TimeOfDay, tuple[int, int]]] = {
    "residential": {
        "day": (1, 20),
        "night": (5, 60),
    },
    "office": {
        "day": (20, 300),
        "night": (0, 30),
    },
    "school": {
        "day": (100, 1200),
        "night": (0, 30),
    },
    "hospital": {
        "day": (100, 1500),
        "night": (80, 1000),
    },
    "shopping_mall": {
        "day": (500, 5000),
        "night": (10, 150),
    },
}

FATALITY_RATIOS: dict[DamageLevel, tuple[float, float]] = {
    "no_damage": (0.0, 0.01),
    "damaged": (0.01, 0.10),
    "collapsed": (0.10, 0.45),
}

BUILDING_AREA_RANGES: dict[BuildingType, tuple[int, int]] = {
    "residential": (80, 200),
    "office": (150, 800),
    "school": (1000, 6000),
    "hospital": (3000, 20000),
    "shopping_mall": (5000, 50000),
}

UNIT_CONSTRUCTION_COST_TRY_PER_M2 = 15000
DEBRIS_REMOVAL_COST_TRY_PER_M2 = 1000
INTERIOR_LOSS_COST_TRY_PER_M2 = 3000

DAMAGE_COST_FACTORS: dict[DamageLevel, dict[str, tuple[float, float]]] = {
    "no_damage": {
        "structural": (0.00, 0.03),
        "debris": (0.00, 0.00),
        "interior": (0.00, 0.05),
    },
    "damaged": {
        "structural": (0.10, 0.45),
        "debris": (0.00, 0.20),
        "interior": (0.05, 0.35),
    },
    "collapsed": {
        "structural": (0.70, 1.00),
        "debris": (0.70, 1.00),
        "interior": (0.60, 0.95),
    },
}

OCCUPANCY_ADJUSTMENTS: dict[OccupancyRange, tuple[float, float]] = {
    "auto": (1.0, 1.0),
    "low": (0.50, 0.70),
    "medium": (0.85, 1.0),
    "high": (1.10, 1.30),
}


def validate_choice(value: str, valid_values: set[str], field_name: str) -> None:
    """Raise a clear error when user input is outside allowed values."""
    if value not in valid_values:
        allowed = ", ".join(sorted(valid_values))
        raise ValueError(f"Invalid {field_name}: '{value}'. Allowed values: {allowed}")


def format_range(min_value: int, max_value: int, unit: str) -> str:
    """Format a numeric range with a readable unit."""
    return f"{min_value:,}-{max_value:,} {unit}"


def format_try_range(loss_range: MoneyRange) -> str:
    """Format a Turkish Lira range without claiming exact precision."""
    min_value, max_value = loss_range
    return f"TL {min_value:,.0f} - TL {max_value:,.0f}"


def estimate_population_range(
    building_type: BuildingType,
    time_of_day: TimeOfDay,
    occupancy_range: OccupancyRange = "auto",
) -> tuple[int, int]:
    """Estimate people inside one building from building type and time."""
    population_min, population_max = POPULATION_RANGES[building_type][time_of_day]
    min_factor, max_factor = OCCUPANCY_ADJUSTMENTS[occupancy_range]

    adjusted_min = round(population_min * min_factor)
    adjusted_max = round(population_max * max_factor)

    return max(0, adjusted_min), max(adjusted_min, adjusted_max)


def estimate_casualty_numbers(
    population_range: tuple[int, int],
    damage_level: DamageLevel,
) -> tuple[int, int]:
    """Estimate a possible casualty range from population and damage severity."""
    population_min, population_max = population_range
    fatality_min, fatality_max = FATALITY_RATIOS[damage_level]

    casualty_min = round(population_min * fatality_min)
    casualty_max = round(population_max * fatality_max)

    return casualty_min, max(casualty_min, casualty_max)


def calculate_risk_level(casualty_max: int) -> RiskLevel:
    """Map maximum possible casualty count to a decision-support risk level."""
    if casualty_max == 0:
        return "very_low"
    if casualty_max < 5:
        return "low"
    if casualty_max < 50:
        return "medium"
    if casualty_max < 250:
        return "high"
    return "critical"


def calculate_loss_component(
    area_range: tuple[int, int],
    unit_cost: int,
    factor_range: tuple[float, float],
) -> MoneyRange:
    """Calculate min/max loss for one economic loss component."""
    area_min, area_max = area_range
    factor_min, factor_max = factor_range

    loss_min = round(area_min * unit_cost * factor_min)
    loss_max = round(area_max * unit_cost * factor_max)

    return loss_min, loss_max


def calculate_economic_loss(
    building_type: BuildingType,
    damage_level: DamageLevel,
) -> tuple[MoneyRange, str, EconomicLossBreakdown]:
    """Estimate economic loss range and component breakdown in Turkish Lira."""
    area_range = BUILDING_AREA_RANGES[building_type]
    cost_factors = DAMAGE_COST_FACTORS[damage_level]

    structural_loss = calculate_loss_component(
        area_range,
        UNIT_CONSTRUCTION_COST_TRY_PER_M2,
        cost_factors["structural"],
    )
    debris_removal = calculate_loss_component(
        area_range,
        DEBRIS_REMOVAL_COST_TRY_PER_M2,
        cost_factors["debris"],
    )
    interior_loss = calculate_loss_component(
        area_range,
        INTERIOR_LOSS_COST_TRY_PER_M2,
        cost_factors["interior"],
    )

    total_min = structural_loss[0] + debris_removal[0] + interior_loss[0]
    total_max = structural_loss[1] + debris_removal[1] + interior_loss[1]

    if total_max < 500_000:
        economic_loss_level = "low"
    elif total_max < 5_000_000:
        economic_loss_level = "medium"
    else:
        economic_loss_level = "high"

    return (
        (total_min, total_max),
        economic_loss_level,
        {
            "structural_loss": format_try_range(structural_loss),
            "debris_removal": format_try_range(debris_removal),
            "interior_loss": format_try_range(interior_loss),
        },
    )


def analyze_risk(
    damage_level: DamageLevel,
    time_of_day: TimeOfDay,
    building_type: BuildingType,
    occupancy_range: OccupancyRange = "auto",
) -> RiskAnalysisResult:
    """Estimate scenario-based risk for one building.

    This function produces decision-support ranges, not exact casualty or
    financial loss predictions.
    """
    validate_choice(damage_level, set(FATALITY_RATIOS), "damage_level")
    validate_choice(time_of_day, {"day", "night"}, "time_of_day")
    validate_choice(building_type, set(POPULATION_RANGES), "building_type")
    validate_choice(occupancy_range, set(OCCUPANCY_ADJUSTMENTS), "occupancy_range")

    population_range = estimate_population_range(building_type, time_of_day, occupancy_range)
    casualty_range = estimate_casualty_numbers(population_range, damage_level)
    risk_level = calculate_risk_level(casualty_range[1])
    total_loss, economic_loss_level, breakdown = calculate_economic_loss(building_type, damage_level)

    return {
        "estimated_population_range": format_range(*population_range, unit="kişi"),
        "estimated_casualty_range": format_range(*casualty_range, unit="olası can kaybı"),
        "risk_level": risk_level,
        "economic_loss_range_try": format_try_range(total_loss),
        "economic_loss_level": economic_loss_level,
        "economic_loss_breakdown": breakdown,
    }


if __name__ == "__main__":
    result = analyze_risk(
        damage_level="collapsed",
        time_of_day="day",
        building_type="school",
        occupancy_range="auto",
    )
    print(result)
