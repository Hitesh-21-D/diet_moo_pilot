
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
    memory_enabled: bool = True
    adaptation_enabled: bool = True
    dual_diversity_enabled: bool = True

    # Pareto archive diversity
    decision_space_diversity_weight: float = 0.30

    # Adaptive search controls
    stagnation_window: int = 10
    diversity_threshold: float = 0.15

    # Repair-search limits
    max_repair_attempts: int = 20

    def __post_init__(self):
        if min(self.population_size, self.max_evaluations, self.archive_size) < 1:
            raise ValueError("Population, budget and archive capacity must be positive")
        if self.max_repair_attempts < 0 or self.stagnation_window < 1:
            raise ValueError("Invalid repair or stagnation limit")
        for value in (self.baseline_seed_fraction, self.habit_guided_mutation_probability,
                      self.decision_space_diversity_weight, self.diversity_threshold):
            if not 0 <= value <= 1:
                raise ValueError("Probabilities and diversity weights must be in [0, 1]")
        for lo, initial, hi in ((self.min_crossover_rate, self.initial_crossover_rate, self.max_crossover_rate),
                                (self.min_mutation_rate, self.initial_mutation_rate, self.max_mutation_rate)):
            if not 0 <= lo <= initial <= hi <= 1:
                raise ValueError("Invalid adaptive rate bounds")


DEFAULT_APPO_CONFIG = APPOConfig()
