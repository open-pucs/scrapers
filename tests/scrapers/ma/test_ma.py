import unittest
from unittest.mock import patch, Mock
from datetime import datetime
from io import open
import os
import requests

from openpuc_scrapers.scrapers import MassachusettsDPU
from openpuc_scrapers.models import GenericCase


class TestMassachusettsDPU(unittest.TestCase):
    def setUp(self):
        """Prepare the initial test setup."""
        # Create a sample case object
        self.case = GenericCase(docket_govid="20-75")

        # Read the desired response HTML file into the test suite
        case_detail_filepath = os.path.join(
            os.path.dirname(__file__), "test_ma_case_page.html"
        )
        with open(case_detail_filepath, "r", encoding="utf-8") as file:
            self.case_detail_html_content = file.read()

        case_list_filepath = os.path.join(
            os.path.dirname(__file__), "test_ma_case_list.html"
        )
        with open(case_list_filepath, "r", encoding="utf-8") as file:
            self.case_list_html_content = file.read()

        # Instantiate the scraper
        self.scraper = MassachusettsDPU()

    @patch("requests.get")
    def test_get_case_details(self, mock_get):
        """Test the get_case_details method."""
        # Mock the response from the requests.get
        mock_response = Mock()
        mock_response.text = self.case_detail_html_content
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

    @patch("requests.get")
    def test_get_all_cases(self, mock_get):
        """Test the get_all_cases method."""
        # Mock the response from requests.get
        mock_response = Mock()
        mock_response.text = self.case_list_html_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call the method
        cases = self.scraper.get_all_cases()

        # Verify correct number of API calls made (one per industry)
        self.assertEqual(mock_get.call_count, len(MassachusettsDPU.INDUSTRIES))

        # Verify the cases were parsed correctly from the HTML
        self.assertTrue(len(cases) > 0)

        # Check a few specific cases from the test HTML
        # (Update these assertions based on your test HTML content)
        electric_case = next(
            (case for case in cases if case.docket_govid == "25-EB-02"), None
        )
        self.assertIsNotNone(electric_case)
        if electric_case:
            self.assertEqual(electric_case.case_type, "electricity broker")
            self.assertEqual(electric_case.industry, "Electric")
            self.assertEqual(electric_case.petitioner, "Via Energy Solutions, LLC")
            self.assertEqual(
                electric_case.description,
                "Application of Via Energy Solutions, LLC to expand Electricity Broker license to include residential customers.",
            )
            self.assertEqual(electric_case.opened_date, datetime(2025, 2, 19).date())

    @patch("requests.get")
    def test_get_all_cases_http_error(self, mock_get):
        """Test get_all_cases when HTTP requests fail."""
        # Mock to simulate HTTP error
        mock_response = Mock()
        mock_response.raise_for_status = Mock(side_effect=requests.HTTPError)
        mock_get.return_value = mock_response

        # Call the method and verify it raises the error
        with self.assertRaises(requests.HTTPError):
            self.scraper.get_all_cases()

    @patch("requests.get")
    def test_get_all_cases_empty_response(self, mock_get):
        """Test get_all_cases when response contains no cases."""
        # Mock empty table response
        empty_html = "Nothing found"
        mock_response = Mock()
        mock_response.text = empty_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call the method
        cases = self.scraper.get_all_cases()

        # Verify result is an empty list
        self.assertEqual(cases, [])


if __name__ == "__main__":
    unittest.main()
