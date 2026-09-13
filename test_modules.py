#!/usr/bin/env python
"""Quick test of form parsing and matching modules."""

from job_automation.forms.parser import FormField, FieldType
from job_automation.forms.matcher import FormMatcher
from job_automation.profile.loader import ProfileLoader

# Test ProfileLoader
loader = ProfileLoader()
profile = loader.load_profile()
answers = loader.load_answers()

print("✓ Profile loaded:")
print(f"  Name: {profile.name}")
print(f"  Email: {profile.email}")
print(f"  Phone: {profile.phone}")

print("\n✓ Answers loaded:")
print(f"  Keys: {list(answers.model_dump(exclude_none=True).keys())}")

# Test FormMatcher
matcher = FormMatcher(profile.model_dump(exclude_none=True), answers.model_dump(exclude_none=True))

# Create test form fields
test_fields = [
    FormField(name="full_name", field_type=FieldType.TEXT, label="Full Name", required=True),
    FormField(name="email_address", field_type=FieldType.EMAIL, label="Email", required=True),
    FormField(name="phone_number", field_type=FieldType.PHONE, label="Phone", required=False),
    FormField(name="why_interested", field_type=FieldType.TEXTAREA, label="Why are you interested?"),
    FormField(name="work_auth", field_type=FieldType.SELECT, label="Work Authorization", options=["Yes", "No"]),
]

print("\n✓ Testing form field matching:")
matches = matcher.match_fields(test_fields)
for match in matches:
    confidence = f"{match.confidence:.0%}" if match.confidence > 0 else "0%"
    value = match.suggested_value[:30] if match.suggested_value else "None"
    print(f"  {match.form_field.name:20} → {value:30} ({confidence})")

print("\n✅ All modules working!")
