import unittest
from pydantic import ValidationError


from openpuc_scrapers.models import GenericAttachment


class TestAttachmentModel(unittest.TestCase):
    def test_valid_attachment(self):
        """Test valid attachment data."""
        attachment = GenericAttachment(
            name="Test Document",
            url="http://example.com/attachment.pdf",
            document_type="PDF",
            full_text="Full content of the attachment",
        )
        self.assertEqual(attachment.name, "Test Document")
        self.assertEqual(str(attachment.url), "http://example.com/attachment.pdf")
        self.assertEqual(attachment.document_type, "PDF")

    def test_missing_optional_fields(self):
        """Test attachment with missing optional fields."""
        attachment = GenericAttachment(
            name="Test Document",
            url="http://example.com/attachment.pdf",
        )
        self.assertEqual(attachment.name, "Test Document")
        self.assertEqual(str(attachment.url), "http://example.com/attachment.pdf")
        self.assertIsNone(attachment.document_type)
        self.assertIsNone(attachment.full_text)

    def test_invalid_url(self):
        """Test invalid URL in the attachment."""
        with self.assertRaises(ValidationError):
            GenericAttachment(filing_id="98765", name="Test Document", url="not-a-valid-url")


if __name__ == "__main__":
    unittest.main()
