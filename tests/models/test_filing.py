import unittest
from datetime import date
from pydantic import ValidationError


from openpuc_scrapers.models import Filing


class TestFilingModel(unittest.TestCase):
    def test_valid_filing(self):
        """Test valid filing data."""
        filing = Filing(
            filed_date=date(2023, 3, 10),
            party_name="XYZ Corp",
            filing_type="Brief",
            description="Filed a legal brief for the case.",
        )
        self.assertEqual(filing.filing_type, "Brief")
        self.assertEqual(filing.party_name, "XYZ Corp")
        self.assertEqual(filing.description, "Filed a legal brief for the case.")

    def test_missing_required_fields(self):
        """Test missing required fields (e.g., filed_date)."""
        with self.assertRaises(ValidationError):
            Filing(
                filing_type="Brief",
                description="A filing without a date",
            )


if __name__ == "__main__":
    unittest.main()
