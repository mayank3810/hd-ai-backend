from bson import ObjectId
from pydantic import BaseModel

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, field=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        # Use the handler to generate the base schema and update it
        json_schema = handler(schema)
        json_schema.update(type="string")
        return json_schema