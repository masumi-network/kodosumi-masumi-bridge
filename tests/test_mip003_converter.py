import pytest
from masumi_kodosuni_connector.services.schema_converter import KodosumyToMIP003Converter
from masumi_kodosuni_connector.api.mip003_schemas import InputType, ValidationRule


def test_convert_simple_text_field():
    """Test conversion of a simple text input field."""
    kodosumi_element = {
        "type": "text",
        "name": "full_name",
        "label": "Full Name",
        "required": True,
        "placeholder": "Enter your full name"
    }
    
    converter = KodosumyToMIP003Converter()
    field = converter._convert_element(kodosumi_element)
    
    assert field is not None
    assert field.id == "full_name"
    assert field.type == InputType.STRING
    assert field.name == "Full Name"
    assert field.data.placeholder == "Enter your full name"
    assert field.validations is None  # No explicit validations since required is default


def test_convert_email_field():
    """Test conversion of an email field with validation."""
    kodosumi_element = {
        "type": "text",
        "name": "email",
        "label": "Email Address",
        "required": True,
        "pattern": "email",
        "min_length": 5,
        "max_length": 100
    }
    
    converter = KodosumyToMIP003Converter()
    field = converter._convert_element(kodosumi_element)
    
    assert field is not None
    assert field.id == "email"
    assert field.type == InputType.STRING
    assert field.name == "Email Address"
    
    # Check validations
    validation_dict = {v.validation: v.value for v in field.validations}
    assert validation_dict["min"] == 5
    assert validation_dict["max"] == 100
    assert validation_dict["format"] == "email"


def test_convert_number_field():
    """Test conversion of a number field."""
    kodosumi_element = {
        "type": "number",
        "name": "age",
        "label": "Age",
        "min_value": 18,
        "max_value": 120,
        "step": 1
    }
    
    converter = KodosumyToMIP003Converter()
    field = converter._convert_element(kodosumi_element)
    
    assert field is not None
    assert field.id == "age"
    assert field.type == InputType.NUMBER
    assert field.name == "Age"
    
    # Check validations
    validation_dict = {v.validation: v.value for v in field.validations}
    assert validation_dict["min"] == 18
    assert validation_dict["max"] == 120
    assert validation_dict["format"] == "integer"


def test_convert_select_field():
    """Test conversion of a select field."""
    kodosumi_element = {
        "type": "select",
        "name": "country",
        "label": "Country",
        "option": [
            {"name": "us", "label": "United States"},
            {"name": "ca", "label": "Canada"},
            {"name": "uk", "label": "United Kingdom"}
        ],
        "multiple": False
    }
    
    converter = KodosumyToMIP003Converter()
    field = converter._convert_element(kodosumi_element)
    
    assert field is not None
    assert field.id == "country"
    assert field.type == InputType.OPTION
    assert field.name == "Country"
    assert field.data.values == ["United States", "Canada", "United Kingdom"]
    
    # Check validations for single selection
    validation_dict = {v.validation: v.value for v in field.validations}
    assert validation_dict["min"] == 1
    assert validation_dict["max"] == 1


def test_convert_optional_field():
    """Test conversion of an optional field."""
    kodosumi_element = {
        "type": "text",
        "name": "middle_name",
        "label": "Middle Name",
        "required": False
    }
    
    converter = KodosumyToMIP003Converter()
    field = converter._convert_element(kodosumi_element)
    
    assert field is not None
    assert field.id == "middle_name"
    assert field.type == InputType.STRING
    assert field.name == "Middle Name"
    
    # Check for optional validation
    validation_dict = {v.validation: v.value for v in field.validations}
    assert validation_dict["optional"] == "true"


def test_convert_boolean_field():
    """Test conversion of a boolean field - should not have optional validation."""
    kodosumi_element = {
        "type": "checkbox",
        "name": "newsletter",
        "label": "Subscribe to Newsletter",
        "required": False
    }
    
    converter = KodosumyToMIP003Converter()
    field = converter._convert_element(kodosumi_element)
    
    assert field is not None
    assert field.id == "newsletter"
    assert field.type == InputType.BOOLEAN
    assert field.name == "Subscribe to Newsletter"
    
    # Boolean fields should not have optional validation (they default to false)
    assert field.validations is None or len([v for v in field.validations if v.validation == "optional"]) == 0


def test_convert_multiple_select_field():
    """Test conversion of a multiple select field - should expect array of integers."""
    kodosumi_element = {
        "type": "select",
        "name": "skills",
        "label": "Skills",
        "option": [
            {"name": "js", "label": "JavaScript"},
            {"name": "py", "label": "Python"},
            {"name": "go", "label": "Go"}
        ],
        "multiple": True,
        "required": False
    }
    
    converter = KodosumyToMIP003Converter()
    field = converter._convert_element(kodosumi_element)
    
    assert field is not None
    assert field.id == "skills"
    assert field.type == InputType.OPTION
    assert field.name == "Skills"
    assert field.data.values == ["JavaScript", "Python", "Go"]
    
    # Check validations for multiple selection with optional
    validation_dict = {v.validation: v.value for v in field.validations}
    assert validation_dict["min"] == 0  # Optional multiple select can have 0 selections
    assert validation_dict["optional"] == "true"


def test_create_simple_schema():
    """Test creation of a simple default schema."""
    converter = KodosumyToMIP003Converter()
    fields = converter.create_simple_schema("Test Flow")
    
    assert len(fields) == 1
    field = fields[0]
    assert field.id == "prompt"
    assert field.type == InputType.STRING
    assert field.name == "Prompt"
    assert "Test Flow" in field.data.description