Store files and file text in a seperate directory called raw_attachments 



# its probably a good idea to keep raw attachments in their own bucket though
a Raw Attachment is just a file, indexed by its hash, 

in raw_attachments/raw is a giant s3 bucket with a bunch of binary files corresponding to the raw binary of each attachment 

in raw_attachments/text is a similarly large bucket with a <hash>.json object, containing the name of said file, its language, the last updated timestamp 


# Objects 

in the /object bucket, I think for now to keep it simple, every single docket gets its own file/ under <state>/<juristiction>/<generic_docket_id>.json

In order to keep a synchronized list of what objects are updated when, keeping a sql database. (To start off with probably a sqlite db, but if we ever actually deploy it to flyte its probably going to be necessary to use postgres.)


