start_index = 0
end_endex = 40000

openscrapers_endpoint = "http://localhost:33399/admin/direct_file_attachment_process"
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

# {
#   "attachment": {
#     "hash": "-rKlk-TDNF_F8bK_yvSj3MB7PcEF7hD3LoIEL9KdIyI=",
#     "jurisdiction_info": {
#       "country": "unknown",
#       "state": "unknown",
#       "jurisdiction": "unknown"
#     },
#     "name": "PDF_TestPage.pdf",
#     "extension": "pdf",
#     "text_objects": [],
#     "date_added": "2025-08-07T11:57:01.089579345Z",
#     "date_updated": "2025-08-07T11:57:01.089582251Z",
#     "extra_metadata": {
#       "server_filename": "PDF_TestPage.pdf"
#     }
#   },
#   "hash": "-rKlk-TDNF_F8bK_yvSj3MB7PcEF7hD3LoIEL9KdIyI=",
#   "server_file_name": "PDF_TestPage.pdf"
# }


def generate_utah_url(number: int) -> str:
    return f"https://dataexplorer.ogm.utah.gov/api/Files?fileName=wellfile|{number}"


for i in range(start_index, end_endex):
    utah_url = generate_utah_url(i)
