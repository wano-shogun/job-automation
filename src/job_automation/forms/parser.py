"""Parse HTML forms and extract fillable fields."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from bs4 import BeautifulSoup
from selenium import webdriver


class FieldType(str, Enum):
    """Types of form fields."""

    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    TEXTAREA = "textarea"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    FILE = "file"
    HIDDEN = "hidden"
    UNKNOWN = "unknown"


@dataclass
class FormField:
    """A form field to be filled."""

    name: str
    field_type: FieldType
    label: Optional[str] = None
    placeholder: Optional[str] = None
    options: list[str] = field(default_factory=list)  # For select/radio/checkbox
    required: bool = False
    element_id: Optional[str] = None
    element_class: Optional[str] = None

    def __repr__(self) -> str:
        """Return a readable representation."""
        return f"FormField(name={self.name}, type={self.field_type}, label={self.label})"


@dataclass
class Form:
    """A complete form with all its fields."""

    form_id: Optional[str]
    form_class: Optional[str]
    fields: list[FormField] = field(default_factory=list)
    submit_button_text: Optional[str] = None

    def __repr__(self) -> str:
        """Return a readable representation."""
        return f"Form(id={self.form_id}, fields={len(self.fields)})"


def parse_forms_from_page(driver: webdriver.Chrome) -> list[Form]:
    """Parse all forms from the current page.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        A list of Form objects found on the page.
    """
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, "html.parser")

    forms = []
    for form_elem in soup.find_all("form"):
        form = _parse_form_element(form_elem)
        forms.append(form)

    return forms


def _parse_form_element(form_elem) -> Form:
    """Parse a single form element.

    Args:
        form_elem: A BeautifulSoup form element.

    Returns:
        A Form object.
    """
    form_id = form_elem.get("id")
    form_class = form_elem.get("class")

    fields = []
    for input_elem in form_elem.find_all(["input", "textarea", "select"]):
        field = _parse_field_element(input_elem)
        if field:
            fields.append(field)

    # Find submit button
    submit_text = None
    submit_button = form_elem.find("button", {"type": "submit"})
    if not submit_button:
        submit_button = form_elem.find("input", {"type": "submit"})
    if submit_button:
        submit_text = submit_button.get_text() or submit_button.get("value")

    return Form(form_id=form_id, form_class=form_class, fields=fields, submit_button_text=submit_text)


def _parse_field_element(elem) -> Optional[FormField]:
    """Parse a single form field element.

    Args:
        elem: A BeautifulSoup input/textarea/select element.

    Returns:
        A FormField object, or None if the field should be skipped.
    """
    elem_name = elem.name
    field_name = elem.get("name")
    field_id = elem.get("id")
    field_class = elem.get("class")

    if not field_name:
        return None

    field_type = FieldType.UNKNOWN
    label = None
    placeholder = None
    options = []
    required = elem.get("required") is not None

    if elem_name == "input":
        input_type = elem.get("type", "text").lower()
        field_type = _map_input_type(input_type)
        placeholder = elem.get("placeholder")
        if input_type == "hidden":
            return None  # Skip hidden fields

    elif elem_name == "textarea":
        field_type = FieldType.TEXTAREA
        placeholder = elem.get("placeholder")

    elif elem_name == "select":
        field_type = FieldType.SELECT
        for option in elem.find_all("option"):
            opt_text = option.get_text().strip()
            opt_value = option.get("value", opt_text)
            if opt_text:  # Skip empty options
                options.append(opt_value)

    # Try to find an associated label
    if field_id:
        label_elem = elem.find_parent("form").find("label", {"for": field_id}) if elem.find_parent("form") else None
        if label_elem:
            label = label_elem.get_text().strip()

    if not label:
        label = field_name

    return FormField(
        name=field_name,
        field_type=field_type,
        label=label,
        placeholder=placeholder,
        options=options,
        required=required,
        element_id=field_id,
        element_class=" ".join(field_class) if field_class else None,
    )


def _map_input_type(input_type: str) -> FieldType:
    """Map HTML input type to FieldType enum.

    Args:
        input_type: The HTML input type attribute.

    Returns:
        The corresponding FieldType.
    """
    mapping = {
        "text": FieldType.TEXT,
        "email": FieldType.EMAIL,
        "tel": FieldType.PHONE,
        "phone": FieldType.PHONE,
        "checkbox": FieldType.CHECKBOX,
        "radio": FieldType.RADIO,
        "file": FieldType.FILE,
        "hidden": FieldType.HIDDEN,
        "submit": FieldType.HIDDEN,
        "button": FieldType.HIDDEN,
    }
    return mapping.get(input_type, FieldType.UNKNOWN)
