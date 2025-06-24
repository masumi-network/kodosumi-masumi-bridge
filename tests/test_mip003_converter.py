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
    # No validations field (removed from model)
    assert not hasattr(field, 'validations')


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
    
    # No validations field (removed from model)
    assert not hasattr(field, 'validations')


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
    
    # No validations field (removed from model)
    assert not hasattr(field, 'validations')


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
    
    # No validations field (removed from model)
    assert not hasattr(field, 'validations')


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
    
    # No validations field (removed from model)
    assert not hasattr(field, 'validations')


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
    
    # No validations field (removed from model)
    assert not hasattr(field, 'validations')


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
    
    # No validations field (removed from model)
    assert not hasattr(field, 'validations')


def test_convert_minimal_field():
    """Test conversion of a minimal field with no extra data."""
    kodosumi_element = {
        "type": "text",
        "name": "simple_field",
        "label": "Simple Field"
    }
    
    converter = KodosumyToMIP003Converter()
    field = converter._convert_element(kodosumi_element)
    
    assert field is not None
    assert field.id == "simple_field"
    assert field.type == InputType.STRING
    assert field.name == "Simple Field"
    
    # Should not have data field when there's no placeholder/description/values
    assert not hasattr(field, 'data') or field.data is None
    # Should not have validations field at all (removed from model)
    assert not hasattr(field, 'validations')


def test_json_output_excludes_null_fields():
    """Test that JSON serialization excludes null/None fields."""
    import json
    
    # Test field with only placeholder
    kodosumi_element = {
        "type": "text",
        "name": "test_field",
        "label": "Test Field",
        "placeholder": "Enter text here"
    }
    
    converter = KodosumyToMIP003Converter()
    field = converter._convert_element(kodosumi_element)
    
    # Convert to JSON and parse back to check structure
    json_str = field.model_dump_json(exclude_unset=True)
    parsed = json.loads(json_str)
    
    # Should have these fields
    assert "id" in parsed
    assert "type" in parsed  
    assert "name" in parsed
    assert "data" in parsed
    assert "placeholder" in parsed["data"]
    
    # Should NOT have these fields
    assert "validations" not in parsed  # Field removed from model
    assert "description" not in parsed["data"]
    assert "values" not in parsed["data"]


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