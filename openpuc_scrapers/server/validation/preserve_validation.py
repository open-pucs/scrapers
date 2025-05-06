import logging
from typing import Tuple


from openpuc_scrapers.db.llm_utils import (
    LlmName,
    get_chat_llm_from_model_name,
    make_sysmsg,
    make_usermsg,
    strip_thinking,
)
from openpuc_scrapers.db.s3_utils import (
    fetch_attachment_data_from_s3,
    fetch_attachment_file_from_s3,
    fetch_case_filing_from_s3,
    push_case_to_s3_and_db,
    push_raw_attach_to_s3_and_db,
)
from openpuc_scrapers.db.s3_wrapper import S3FileManager
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.constants import OPENSCRAPERS_S3_OBJECT_BUCKET
from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.hashes import Blake2bHash
from openpuc_scrapers.models.raw_attachments import RawAttachment
from openpuc_scrapers.pipelines.raw_attachment_handling import (
    download_file_from_url_to_path,
    generate_initial_attachment_text,
)

default_logger = logging.getLogger(__name__)


async def rectify_filing_mutate(filing: GenericFiling) -> bool:
    # if filing.name == "" and len(filing.attachments) > 0:
    if len(filing.attachments) > 0:
        if len(filing.attachments) == 1:
            filing.name = filing.attachments[0].name
            return True

        # LLM prompt to select best attachment name
        langchain_llm = get_chat_llm_from_model_name(LlmName.Regular)
        attachment_names = [att.name for att in filing.attachments]

        prompt = f"""Analyze these legal document attachment names and synthesize the most appropriate
        filing name.  If multiple file names exist like  <FILENAME> (Cover Letter), or <FILENAME> (Main Body)
        return the bare file name <FILENAME>. If you tried to identify a pattern and couldnt find one return the 
        name of the documentthat looks the most like it could be the main one main like complaints, 
        petitions, or judgments.
        RETURN YOUR BEST GUESS OF THE NAME AND NOTHING ELSE.
        
        Options:
        {chr(10).join(f"{i}: {name}" for i, name in enumerate(attachment_names))}
        
        Best name:"""

        try:
            response = await langchain_llm.ainvoke([make_usermsg(content=prompt)])
            response_content = response.content
            assert isinstance(response_content, str), "Did not respond with string."
            assert response_content is not None, "Response content is none"
            chosen_name = strip_thinking(response_content)
            default_logger.info(
                f"Recalculated and selected {chosen_name} for document."
            )
            filing.name = chosen_name
        except (ValueError, IndexError):
            default_logger.warning("LLM name selection failed, using first attachment")
            filing.name = filing.attachments[0].name

        return True
    return False


async def rectify_case_raw(input: GenericCase) -> Tuple[bool, GenericCase]:
    did_rectify = False
    filings = input.filings
    if filings is None:
        default_logger.warning(f"Encountered case {input.case_number} with no filings")
        return (False, input)
    for filing in filings:
        rectified_filing = await rectify_filing_mutate(filing=filing)
        did_rectify = did_rectify or rectified_filing
    return (did_rectify, input)


async def fetch_and_rectify_case(
    case_name: str,
    jurisdiction_name: str,
    state: str,
    country: str = "usa",
    rectify: bool = True,
) -> GenericCase:
    case = await fetch_case_filing_from_s3(
        case_name=case_name,
        jurisdiction_name=jurisdiction_name,
        state=state,
        country=country,
    )
    if not rectify:
        return case
    (did_rectify, output_case) = await rectify_case_raw(case)
    if not did_rectify:
        return case
    await push_case_to_s3_and_db(
        case=output_case,
        jurisdiction_name=jurisdiction_name,
        state=state,
        country=country,
    )
    return output_case


async def rectify_raw_attachment_raw(
    attachment: RawAttachment,
) -> Tuple[bool, RawAttachment]:
    if len(attachment.text_objects) > 0:
        did_rectify = False
        return (did_rectify, attachment)
    if attachment.extension != "pdf":
        default_logger.info("Found non pdf data with no text data. Skipping.")
        did_rectify = False
        return (did_rectify, attachment)
    filepath = await fetch_attachment_file_from_s3(attachment.hash)
    text_obj = await generate_initial_attachment_text(
        raw_attach=attachment, file_path=filepath
    )
    if text_obj is None:
        raise Exception(
            f"Failed to process pdf text for raw attachment: {attachment.hash} dispite the document being a pdf."
        )
    attachment.text_objects = [text_obj]
    did_rectify = True
    return (did_rectify, attachment)


async def fetch_and_rectify_raw_attachment_metadata(
    hash: Blake2bHash,
    rectify: bool = True,
) -> RawAttachment:
    raw_attachment_metadata = await fetch_attachment_data_from_s3(hash=hash)
    if not rectify:
        return raw_attachment_metadata
    (did_rectify, output_metadata) = await rectify_raw_attachment_raw(
        attachment=raw_attachment_metadata
    )
    if not did_rectify:
        return raw_attachment_metadata
    # Attachment data is already in s3. So you can exclude the path here, and it will error if not present.
    await push_raw_attach_to_s3_and_db(raw_att=raw_attachment_metadata, file_path=None)
    return output_metadata
