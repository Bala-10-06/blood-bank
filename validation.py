from typing import Any, Dict


BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


def validate_registration(form: Dict[str, Any]) -> list[str]:
    errors = []
    required_fields = [
        "user_id",
        "password",
        "aadhar",
        "name",
        "blood_group",
        "age",
        "height",
        "weight",
        "address",
        "phone_number",
        "bad_habits",
    ]

    for field in required_fields:
        if not str(form.get(field, "")).strip():
            errors.append(f"{field.replace('_', ' ').title()} is required.")

    if errors:
        return errors

    if form["blood_group"] not in BLOOD_GROUPS:
        errors.append("Please select a valid blood group.")

    if form["bad_habits"] not in {"Yes", "No"}:
        errors.append("Please choose Yes or No for bad habits.")

    if not form["aadhar"].isdigit() or len(form["aadhar"]) != 12:
        errors.append("Aadhar must contain exactly 12 digits.")

    if not form["phone_number"].isdigit() or len(form["phone_number"]) != 10:
        errors.append("Phone number must contain exactly 10 digits.")

    try:
        age = int(form["age"])
        if age < 18 or age > 55:
            errors.append("Age must be between 18 and 55.")
    except ValueError:
        errors.append("Age must be a number.")

    try:
        height = float(form["height"])
        if height < 120 or height > 220:
            errors.append("Height must be between 120 cm and 220 cm.")
    except ValueError:
        errors.append("Height must be a number.")

    try:
        weight = float(form["weight"])
        if weight < 45 or weight > 200:
            errors.append("Weight must be between 45 kg and 200 kg.")
    except ValueError:
        errors.append("Weight must be a number.")

    return errors
