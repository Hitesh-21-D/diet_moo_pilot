from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Register(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

class Login(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class ProfileInput(StrictModel):
    age: int = Field(ge=18, le=90)
    sex: Literal['male', 'female']
    height_cm: float = Field(ge=120, le=230)
    weight_kg: float = Field(ge=30, le=250)
    activity_factor: Literal[1.2, 1.375, 1.55, 1.725, 1.9]
    goal: Literal['weight_gain', 'weight_loss', 'maintenance']
    calorie_adjustment: float = Field(ge=0, le=750)
    @model_validator(mode='after')
    def maintenance(self):
        if self.goal == 'maintenance':
            self.calorie_adjustment = 0
        return self

class FoodInput(StrictModel):
    food_code: str = Field(min_length=1, max_length=30)
    servings: float = Field(gt=0, le=20)

class DayInput(StrictModel):
    label: str = Field(min_length=1, max_length=100)
    date: date
    diet: dict[str, list[FoodInput]]

class SubmissionInput(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    days: list[DayInput] = Field(min_length=1, max_length=14)

Algorithm = Literal['NSGA-II','NSGA-III','MOEA/D','SPEA2','MOPSO','APPO','APPO-NoRepair']
class ExperimentInput(StrictModel):
    day_ids: list[str] = Field(min_length=1, max_length=14)
    algorithms: list[Algorithm] = Field(min_length=1, max_length=7)
    seeds: list[int] = Field(default=[42], min_length=1, max_length=30)
    budget: int = Field(default=15000, ge=100, le=15000)
    @model_validator(mode='after')
    def unique(self):
        if any(len(x) != len(set(x)) for x in (self.day_ids, self.algorithms, self.seeds)):
            raise ValueError('Days, algorithms and seeds must be unique')
        if any(s < 0 or s > 2**32-1 for s in self.seeds):
            raise ValueError('Seeds must be unsigned 32-bit integers')
        if len(self.day_ids)*len(self.algorithms)*len(self.seeds) > 210:
            raise ValueError('At most 210 runs per request')
        return self
