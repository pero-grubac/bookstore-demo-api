from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Fantasy"])


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    # Omitted fields stay unchanged; `name` may be omitted but not set to null.
    name: str = Field(default=None, min_length=1, max_length=100)


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
