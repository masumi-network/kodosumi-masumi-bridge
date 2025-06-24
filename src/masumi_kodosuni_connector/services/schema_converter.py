from typing import Dict, Any, List, Optional
from masumi_kodosuni_connector.api.mip003_schemas import InputField, InputType, ValidationRule, InputData


class KodosumyToMIP003Converter:
    """Converts Kodosumi form schema to MIP-003 input schema format."""
    
    @staticmethod
    def convert_kodosumi_schema(kodosumi_schema: Dict[str, Any]) -> List[InputField]:
        """Convert Kodosumi form schema to MIP-003 InputField list."""
        input_fields = []
        
        # Kodosumi schemas contain form elements directly in the schema
        # Each element has properties like type, name, label, etc.
        if isinstance(kodosumi_schema, list):
            form_elements = kodosumi_schema
        else:
            form_elements = kodosumi_schema.get("form", kodosumi_schema.get("elements", []))
        
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
            "inputtext": InputType.STRING,
            "inputnumber": InputType.NUMBER,
            "number": InputType.NUMBER,
            "inputemail": InputType.STRING,
            "inputurl": InputType.STRING,
            "inputpassword": InputType.STRING,
            "textarea": InputType.STRING,
            "select": InputType.OPTION,
            "checkbox": InputType.BOOLEAN,
            "radio": InputType.OPTION,
            "slider": InputType.NUMBER,
            "switch": InputType.BOOLEAN,
            "fileupload": InputType.STRING,
            "html": InputType.NONE,
            "markdown": InputType.NONE,
            "submit": InputType.NONE,
            "cancel": InputType.NONE,
        }
        
        # Handle unsupported types by converting to string with format instructions
        unsupported_types = {
            "date": {
                "type": InputType.STRING,
                "format": "date",
                "description": "Enter date in YYYY-MM-DD format (e.g., 2024-12-25)"
            },
            "time": {
                "type": InputType.STRING,
                "format": "time", 
                "description": "Enter time in HH:MM format (e.g., 14:30)"
            },
            "datetime": {
                "type": InputType.STRING,
                "format": "datetime",
                "description": "Enter datetime in YYYY-MM-DD HH:MM format (e.g., 2024-12-25 14:30)"
            },
            "file": {
                "type": InputType.STRING,
                "format": "file",
                "description": "Enter file path or URL"
            },
            "color": {
                "type": InputType.STRING,
                "format": "color",
                "description": "Enter color in hex format (e.g., #FF0000) or color name"
            }
        }
        
        mip003_type = type_mapping.get(element_type)
        unsupported_mapping = unsupported_types.get(element_type)
        
        if unsupported_mapping:
            mip003_type = unsupported_mapping["type"]
        elif not mip003_type or mip003_type == InputType.NONE:
            return None
        
        # Extract basic info - Kodosumi uses 'name' for field ID and 'label' for display name
        field_id = element.get("name", f"field_{hash(str(element))}")
        field_name = element.get("label", element.get("text", field_id))
        
        # Build input data
        input_data = InputData()
        
        # Add description/placeholder if available
        if "placeholder" in element:
            input_data.placeholder = element["placeholder"]
        if "description" in element:
            input_data.description = element["description"]
        
        # Add format-specific description for unsupported types
        if unsupported_mapping:
            format_description = unsupported_mapping["description"]
            if input_data.description:
                input_data.description = f"{input_data.description} | {format_description}"
            else:
                input_data.description = format_description
        
        # Handle option type values (Select, Radio)
        if mip003_type == InputType.OPTION:
            values = []
            # Check for different option formats
            if "options" in element:
                options = element["options"] if isinstance(element["options"], list) else [element["options"]]
                for opt in options:
                    if isinstance(opt, dict):
                        # Option can have 'label' and 'value' properties
                        values.append(opt.get("label", opt.get("value", str(opt))))
                    else:
                        values.append(str(opt))
            elif "option" in element:
                options = element["option"] if isinstance(element["option"], list) else [element["option"]]
                for opt in options:
                    if isinstance(opt, dict):
                        # Option can have 'label', 'name' and 'value' properties
                        values.append(opt.get("label", opt.get("name", opt.get("value", str(opt)))))
                    else:
                        values.append(str(opt))
            
            if values:
                input_data.values = values
        
        # No validations - keeping it simple
        validations = None
        
        return InputField(
            id=field_id,
            type=mip003_type,
            name=field_name,
            data=input_data if input_data.placeholder or input_data.values or input_data.description else None,
            validations=None
        )
    
    @staticmethod
    def convert_mip003_to_kodosumi(input_data: Dict[str, Any], kodosumi_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MIP-003 input data to Kodosumi execution format."""
        # Extract form elements from Kodosumi schema
        if isinstance(kodosumi_schema, list):
            form_elements = kodosumi_schema
        else:
            form_elements = kodosumi_schema.get("form", kodosumi_schema.get("elements", []))
        
        # Create mapping from field names to Kodosumi element names
        field_mapping = {}
        for element in form_elements:
            element_name = element.get("name")
            if element_name:
                field_mapping[element_name] = element_name
        
        # Convert input data using the mapping
        converted_data = {}
        for field_id, value in input_data.items():
            kodosumi_field = field_mapping.get(field_id, field_id)
            converted_data[kodosumi_field] = value
        
        return converted_data
    
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
                validations=None
            )
        ]