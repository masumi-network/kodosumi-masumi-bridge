from typing import Dict, Any, List, Optional
from masumi_kodosuni_connector.api.mip003_schemas import InputField, InputType, ValidationRule, InputData


class KodosumyToMIP003Converter:
    """Converts Kodosumi form schema to MIP-003 input schema format."""
    
    @staticmethod
    def convert_kodosumi_schema(kodosumi_schema: Dict[str, Any]) -> List[InputField]:
        """Convert Kodosumi form schema to MIP-003 InputField list."""
        input_fields = []
        
        # Kodosumi schemas typically contain form elements
        form_elements = kodosumi_schema.get("form", [])
        
        for element in form_elements:
            input_field = KodosumyToMIP003Converter._convert_element(element)
            if input_field:
                input_fields.append(input_field)
        
        return input_fields
    
    @staticmethod
    def _convert_element(element: Dict[str, Any]) -> Optional[InputField]:
        """Convert a single Kodosumi form element to MIP-003 InputField."""
        element_type = element.get("type", "").lower()
        
        # Map Kodosumi types to MIP-003 types
        type_mapping = {
            "text": InputType.STRING,
            "textarea": InputType.STRING,
            "password": InputType.STRING,
            "number": InputType.NUMBER,
            "boolean": InputType.BOOLEAN,
            "select": InputType.OPTION,
            "option": InputType.OPTION,
            "html": InputType.NONE,
            "markdown": InputType.NONE,
        }
        
        mip003_type = type_mapping.get(element_type)
        if not mip003_type:
            return None
        
        # Extract basic info
        field_id = element.get("name", element.get("id", f"field_{hash(str(element))}"))
        field_name = element.get("label", element.get("text", field_id))
        
        # Build input data
        input_data = InputData()
        
        # Add description if available
        if "placeholder" in element:
            input_data.placeholder = element["placeholder"]
        
        # Handle option type values
        if mip003_type == InputType.OPTION and "option" in element:
            values = []
            options = element["option"] if isinstance(element["option"], list) else [element["option"]]
            for opt in options:
                if isinstance(opt, dict):
                    values.append(opt.get("label", opt.get("name", str(opt))))
                else:
                    values.append(str(opt))
            input_data.values = values
        
        # Build validations
        validations = []
        
        # Handle required field
        if element.get("required", False):
            # Don't add optional=false since all fields are required by default in MIP-003
            pass
        else:
            validations.append(ValidationRule(validation="optional", value=True))
        
        # Handle specific validations based on type
        if mip003_type == InputType.STRING:
            if "min_length" in element:
                validations.append(ValidationRule(validation="min", value=element["min_length"]))
            if "max_length" in element:
                validations.append(ValidationRule(validation="max", value=element["max_length"]))
            if "pattern" in element and element["pattern"] == "email":
                validations.append(ValidationRule(validation="format", value="email"))
        
        elif mip003_type == InputType.NUMBER:
            if "min_value" in element:
                validations.append(ValidationRule(validation="min", value=element["min_value"]))
            if "max_value" in element:
                validations.append(ValidationRule(validation="max", value=element["max_value"]))
            if element.get("step") == 1:
                validations.append(ValidationRule(validation="format", value="integer"))
        
        elif mip003_type == InputType.OPTION:
            # For select/option fields, determine min/max selections
            if element.get("multiple", False):
                # Multiple selection allowed
                validations.append(ValidationRule(validation="min", value=0))
                if "max_selections" in element:
                    validations.append(ValidationRule(validation="max", value=element["max_selections"]))
            else:
                # Single selection
                validations.append(ValidationRule(validation="min", value=1))
                validations.append(ValidationRule(validation="max", value=1))
        
        return InputField(
            id=field_id,
            type=mip003_type,
            name=field_name,
            data=input_data if input_data.placeholder or input_data.values else None,
            validations=validations if validations else None
        )
    
    @staticmethod
    def create_simple_schema(flow_name: str) -> List[InputField]:
        """Create a simple default schema when Kodosumi schema is not available."""
        return [
            InputField(
                id="prompt",
                type=InputType.STRING,
                name="Prompt",
                data=InputData(
                    description=f"Input prompt for {flow_name}",
                    placeholder="Enter your request here..."
                ),
                validations=[
                    ValidationRule(validation="min", value=1),
                    ValidationRule(validation="format", value="nonempty")
                ]
            )
        ]