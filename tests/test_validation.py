from validation import validate_registration


def valid_form():
    return {
        "user_id": "donor1",
        "password": "secret123",
        "aadhar": "123456789012",
        "name": "Test Donor",
        "blood_group": "O+",
        "age": "25",
        "height": "170",
        "weight": "70",
        "address": "123 Main Street",
        "phone_number": "9876543210",
        "bad_habits": "No",
    }


def test_valid_registration_has_no_errors():
    assert validate_registration(valid_form()) == []


def test_age_must_be_between_18_and_55():
    form = valid_form()
    form["age"] = "17"
    assert "Age must be between 18 and 55." in validate_registration(form)


def test_height_and_weight_limits_are_enforced():
    form = valid_form()
    form["height"] = "100"
    form["weight"] = "40"
    errors = validate_registration(form)
    assert "Height must be between 120 cm and 220 cm." in errors
    assert "Weight must be between 45 kg and 200 kg." in errors
