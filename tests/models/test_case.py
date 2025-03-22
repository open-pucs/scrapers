import unittest
from datetime import date
from pydantic import ValidationError

from openpuc_scrapers.models import GenericCase


class TestCaseModel(unittest.TestCase):
    def test_valid_case(self):
        """Test valid case data."""
        case = GenericCase(
            case_number="12345",
            case_type="Regulatory",
            description="A regulatory case regarding energy tariffs.",
            industry="Energy",
            petitioner="XYZ Corp",
            hearing_officer="John Doe",
            opened_date=date(2023, 1, 15),
            closed_date=date(2023, 5, 20),
        )
        self.assertEqual(case.case_number, "12345")
        self.assertEqual(case.case_type, "Regulatory")
        self.assertEqual(case.industry, "Energy")

    def test_missing_optional_fields(self):
        """Test case where optional fields are missing."""
        case = GenericCase(case_number="67890", opened_date=date(2023, 7, 1))
        self.assertEqual(case.case_number, "67890")
        self.assertIsNone(case.case_type)
        self.assertIsNone(case.description)
        self.assertIsNone(case.closed_date)

    def test_invalid_date_format(self):
        """Test invalid date format."""
        with self.assertRaises(ValidationError):
            GenericCase(case_number="12345", opened_date="not-a-date")


if __name__ == "__main__":
    unittest.main()
