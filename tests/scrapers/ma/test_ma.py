import unittest
from unittest.mock import patch, Mock
from datetime import datetime
from io import open
import os
import requests

from openpuc_scrapers.scrapers import MassachusettsDPU
from openpuc_scrapers.models import Case


class TestMassachusettsDPU(unittest.TestCase):
    def setUp(self):
        """Prepare the initial test setup."""
        # Create a sample case object
        self.case = Case(case_number="20-75")

        # Read the desired response HTML file into the test suite
        filepath = os.path.join(os.path.dirname(__file__), "test_ma_case_page.html")
        with open(filepath, "r", encoding="utf-8") as file:
            self.html_content = file.read()

        # Instantiate the scraper
        self.scraper = MassachusettsDPU()

    @patch("requests.get")
    def test_get_case_details(self, mock_get):
        """Test the get_case_details method."""
        # Mock the response from the requests.get
        mock_response = Mock()
        mock_response.text = self.html_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call the method
        case = self.scraper.get_case_details(self.case)

        # Assertions to check if case details are populated correctly
        self.assertEqual(case.case_type, "Investigation")
        self.assertEqual(case.industry, "Electric")
        self.assertEqual(
            case.description,
            "Investigation by the Department of Public Utilities On Its Own Motion Into Electric Distribution Companies’ (1) Distributed Energy Resource Planning and (2) Assignment and Recovery of Costs for the Interconnection of Distributed Generation.",
        )
        self.assertEqual(case.petitioner, "DPU")
        self.assertEqual(case.hearing_officer, "ZILGME, KATIE")
        self.assertEqual(case.opened_date, datetime(2020, 10, 22).date())
        self.assertIsNone(case.closed_date)

    @patch("requests.get")
    def test_get_case_details_error(self, mock_get):
        """Test the case where an HTTP error occurs during fetching details."""
        # Simulate a request error (e.g., 404 or 500 response)
        mock_response = Mock()
        mock_response.raise_for_status = Mock(side_effect=requests.HTTPError)
        mock_get.return_value = mock_response

        # Call the method and assert that an error is raised
        with self.assertRaises(requests.HTTPError):
            self.scraper.get_case_details(self.case)


if __name__ == "__main__":
    unittest.main()
