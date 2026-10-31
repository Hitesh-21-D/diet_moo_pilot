
from dataclasses import dataclass


@dataclass(frozen=True)
class APPOConfig:
    # Population and evaluation settings
    population_size: int = 100
    max_evaluations: int = 15000
    archive_size: int = 100
    seed: int = 42

    # Knowledge-guided initialization
    baseline_seed_fraction: float = 0.30

    # Adaptive evolutionary operators
    initial_crossover_rate: float = 0.90
    min_crossover_rate: float = 0.65
    max_crossover_rate: float = 0.95

    initial_mutation_rate: float = 0.20
    min_mutation_rate: float = 0.05
    max_mutation_rate: float = 0.40

    # Personalized optimization
    habit_guided_mutation_probability: float = 0.35
    repair_enabled: bool = True

    # Pareto archive diversity
    decision_space_diversity_weight: float = 0.30

    # Adaptive search controls
    stagnation_window: int = 10
    diversity_threshold: float = 0.15

    # Repair-search limits
    max_repair_attempts: int = 20


DEFAULT_APPO_CONFIG = APPOConfig()
