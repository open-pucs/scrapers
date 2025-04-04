from openpuc_scrapers.models.hashes import Blake2bHash
from openpuc_scrapers.models.raw_attachments import (
    RawAttachment,
    RawAttachmentText,
)


def get_highest_quality_text(attach: RawAttachment) -> str:
    def attach_ranker(att: RawAttachmentText):
        # Scale down timestamp to be a small fraction so quality remains primary factor
        # timestamp_value = att.time.timestamp() / (2**32)  # breaks on unix 2038
        # return att.quality.value + timestamp_value
        return att.quality.value

    best_attachment_text = max(attach.text_objects, key=attach_ranker)
    return best_attachment_text.text
