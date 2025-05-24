in the process of running the create_scraper_allcases_dag in
/home/nicole/Documents/mycorrhizae/open-scrapers/airflow_dags/generate_all_dags.py
specifically the task process_concurrent_cases_airflow the server seems to be running out of memory and crashing. are there any optimisations you could make to the python code to prevent this error?

The architecture with redis is chosen for a specific reason. For example, running this for new york involves handling 35,000 dockets. And declaring each one of those as a task will instantly nuke any computer that tries to run it. So throwing everything in a redis db works well for this. Just try to make optimisations to the existing architecture that would help prevent any memory leaks while it tries to process those 35,000 dockets over the course of a couple days.
