import re

start_index = 0
end_endex = 40000


def transform_filename_to_api_number(file_name: str) -> str:
    # Remove everything that is not a digit.
    digits = re.sub(r"\D", "", file_name)

    # Locate the first occurrence of the prefix "430".
    start = digits.find("430")
    if start == -1:
        return "unknown"

    # Extract exactly 10 digits starting at that point.
    api = digits[start : start + 10]

    # Validate length.
    if len(api) != 10:
        return "unknown"
    return api


openscrapers_endpoint = "http://localhost:33399/admin/direct_file_attachment_process"
# Send it to this endpoint with this schema
# {
#     "extension": "pdf",
#     "fetch_info": {
#         "decode_method": "None",
#         "request_type": "Get",
#         "url": "https://www.cte.iup.edu/cte/Resources/PDF_TestPage.pdf",
#     },
#     "jurisdiction_info": {
#         "country": "unknown",
#         "jurisdiction": "unknown",
#         "state": "unknown",
#     },
#     "process_text_before_upload": false,
#     "wait_for_s3_upload": true,
# }
# and this is the return schema
# {
#   "attachment": {
#     "hash": "-rKlk-TDNF_F8bK_yvSj3MB7PcEF7hD3LoIEL9KdIyI=",
#     "jurisdiction_info": {
#       "country": "unknown",
#       "state": "unknown",
#       "jurisdiction": "unknown"
#     },
#     "name": "PDF_TestPage.pdf",
#     "url": "https://www.cte.iup.edu/cte/Resources/PDF_TestPage.pdf",
#     "extension": "pdf",
#     "text_objects": [],
#     "date_added": "2025-08-07T12:42:03.241348333Z",
#     "date_updated": "2025-08-07T12:42:03.241349796Z",
#     "extra_metadata": {
#       "server_filename": "PDF_TestPage.pdf"
#     }
#   },
#   "hash": "-rKlk-TDNF_F8bK_yvSj3MB7PcEF7hD3LoIEL9KdIyI=",
#   "server_file_name": "PDF_TestPage.pdf",
#   "file_s3_uri": "https://openscrapers.sfo3.digitaloceanspaces.com/raw/file/-rKlk-TDNF_F8bK_yvSj3MB7PcEF7hD3LoIEL9KdIyI=",
#   "object_s3_uri": "https://openscrapers.sfo3.digitaloceanspaces.com/raw/metadata/-rKlk-TDNF_F8bK_yvSj3MB7PcEF7hD3LoIEL9KdIyI=.json"
# }


def generate_utah_url(number: int) -> str:
    return f"https://dataexplorer.ogm.utah.gov/api/Files?fileName=wellfile|{number}"


for i in range(start_index, end_endex):
    # In this code go ahead and hit the openscrapers endpoint with the utah url subsituted in
    utah_url = generate_utah_url(i)
    # then if the transfer was successful go ahead and save the response json under backup/{i}.json
    # then keep a running list of csv results, in the following schema.
    # file_index, hash, url, server_filename, API number guess, file_s3_uri
