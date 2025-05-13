
Here is the beginnings of the thing 
```py
class CrimsonPDFIngestParamsS3(BaseModel):
    s3_uri: str
    langs: Optional[str] = None
    force_ocr: Optional[bool] = None
    paginate: Optional[bool] = None
    disable_image_extraction: Optional[bool] = None
    max_pages: Optional[int] = None


class DocStatusResponse(BaseModel):
    request_id: str
    request_check_url: str
    request_check_leaf: str
    markdown: Optional[str] = None
    status: str
    success: bool
    images: Optional[dict[str, str]] = None
    metadata: Optional[dict[str, str]] = None
    error: Optional[str] = None


async def process_pdf_text_using_crimson(att: GenericAttachment, s3_key: str) -> str:
    hash = att.hash
    assert hash is not None
    file_key = get_raw_attach_file_key(hash)
    s3_url = generate_s3_object_uri_from_key(file_key)
    crimson_params = CrimsonPDFIngestParamsS3(s3_uri=s3_url)
    base_url = CRIMSON_URL
    

    return "blaah"
```

I want you to post the crimson params to 
/v1/ingest/s3

and then take the request_check_leaf add the base_url too it and poll the resulting url with a get request once every 3 seconds until the success boolean is true, then return the markdown element. Use asyncio in python if possible.
