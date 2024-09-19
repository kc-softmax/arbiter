import json
from pydantic import BaseModel
from pathlib import Path
from tempfile import TemporaryDirectory
from datamodel_code_generator import InputFileType, generate
from datamodel_code_generator import DataModelType


def pydantic_from_schema(schema: dict) -> BaseModel:
    model_name = schema.get('title')
    namespace = {}

    schema = json.dumps(schema)
    with TemporaryDirectory() as temporary_directory_name:
        temporary_directory = Path(temporary_directory_name)
        output = Path(temporary_directory / 'model.py')
        generate(
            schema,
            input_file_type=InputFileType.JsonSchema,
            output=output,
            output_model_type=DataModelType.PydanticV2BaseModel,
        )
        model = output.read_text()
        exec(model, namespace)
        return namespace[model_name]
    raise Exception('Failed to generate model')