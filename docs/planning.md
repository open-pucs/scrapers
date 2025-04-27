Store files and file text in a seperate directory called raw_attachments 



# its probably a good idea to keep raw attachments in their own bucket though
a Raw Attachment is just a file, indexed by its hash, 

in raw_attachments/raw is a giant s3 bucket with a bunch of binary files corresponding to the raw binary of each attachment 

in raw_attachments/text is a similarly large bucket with a <hash>.json object, containing the name of said file, its language, the last updated timestamp 


# Objects 

in the /object bucket, I think for now to keep it simple, every single docket gets its own file/ under <state>/<jurisdiction>/<generic_docket_id>.json

In order to keep a synchronized list of what objects are updated when, keeping a sql database. (To start off with probably a sqlite db, but if we ever actually deploy it to flyte its probably going to be necessary to use postgres.)


# INTRUSIVE THOUGHT: Rust GRPC for handling database calls - nic

So currently every python call for database and s3 stuff has native interfaces in python directly to interact with all those resources. There is also another service in this same library that goes ahead and does even more DB interactions to serve the results to end users. 

However, horrible idea. You could go ahead and throw all the database stuff into its own monolith that also serves database requests to the end user, and write it in something like go/rust. Then all the python code in airflow just communicates with the SQL processor/api monolith using GRPC.

Really nice because you don't have to manage DB connection inside python. Plus you can move some of the more important and mission critical code cordoned off, thus helping with SOC. It doesn't even increase the number of services, since the API server needs to be seperate from all the airflow code.

Mainly a bad idea because it increases networking complexity. And adds 2 bits of complexity in Rust/Go, and GRPC that would really hurt maintainability of this since its a public project.

Also the benefits are a bit speculative, because hopefully (tmcr) now that the initial code is stable the postgres and s3 code maintenance burden shouldn't be that big compared to maintaining the individual scraper code to even be worth it. 


