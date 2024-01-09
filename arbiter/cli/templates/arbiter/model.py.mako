# DO NOT DELETE THIE LINE
# USE IT FOR CREATE CUSTOM DATABASE TABLE
from arbiter.api.models import PKModel, BaseSQLModel

# Define your custom table.
# Example
# from sqlmodel import Field, Relationship
# from arbiter.api.models import PKModel

# class MyCustomModelBase(BaseSQLModel):
#    someting_number_value: int = Field(default=0)

# class MyCustomModel(MyCustomModelBase, PKModel, table=True):
#    __tablename__ = "my_custom" # Table name used by the DB