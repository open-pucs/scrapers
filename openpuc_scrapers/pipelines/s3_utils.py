class S3FileManager:
    def __init__(self, logger: Optional[Any] = None) -> None:
        if logger is None:
            logger = default_logger
        self.tmpdir = OS_TMPDIR
        self.rawfile_savedir = OS_HASH_FILEDIR
        self.metadata_backupdir = OS_BACKUP_FILEDIR
        self.endpoint = S3_ENDPOINT
        self.logger = logger

        # Create directories if they don't exist
        self.tmpdir.mkdir(parents=True, exist_ok=True)
        self.rawfile_savedir.mkdir(parents=True, exist_ok=True)
        self.metadata_backupdir.mkdir(parents=True, exist_ok=True)

        self.s3 = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name=CLOUD_REGION,
        )
        self.bucket = S3_FILE_BUCKET
        self.s3_raw_directory = "raw/"

    async def save_filepath_to_hash_async(
        self, filepath: Path, hashpath: Optional[Path] = None, network: bool = True
    ) -> SaveFilepathToHashResult:
        return await asyncio.to_thread(
            self.save_filepath_to_hash, filepath, hashpath, network
        )

    def save_filepath_to_hash(
        self, filepath: Path, hashpath: Optional[Path] = None, network: bool = True
    ) -> SaveFilepathToHashResult:
        did_exist = False
        if hashpath is None:
            hashpath = self.rawfile_savedir
        filepath.parent.mkdir(exist_ok=True, parents=True)
        self.logger.info("Getting hash")
        b264_hash = self.get_blake2_str(filepath)
        self.logger.info(f"Got hash {b264_hash}")
        saveloc = self.get_default_filepath_from_hash(b264_hash, hashpath)

        self.logger.info(f"Saving file to {saveloc}")
        shutil.copyfile(filepath, saveloc)
        if saveloc.exists():
            self.logger.info(f"Successfully Saved File to: {saveloc}")
        else:
            self.logger.error(f"File could not be saved to : {saveloc}")
        if network:
            self.push_raw_file_to_s3(saveloc, b264_hash)
        return SaveFilepathToHashResult(path=saveloc, hash=b264_hash, did_exist=False)

    def get_default_filepath_from_hash(
        self, hash: str, hashpath: Optional[Path] = None
    ) -> Path:
        if hashpath is None:
            hashpath = self.rawfile_savedir
        hashpath.parent.mkdir(exist_ok=True, parents=True)
        saveloc = hashpath / Path(hash)
        if saveloc.exists():
            self.logger.info(f"File already at {saveloc}, do not copy any file to it.")
        return saveloc

    def backup_metadata_to_hash(self, metadata: dict, hash: str) -> Path:
        def backup_metadata_to_filepath(metadata: dict, filepath: Path) -> Path:
            with open(filepath, "w+") as ff:
                yaml.dump(metadata, ff)
            return filepath

        savedir = self.metadata_backupdir / Path(str(hash) + ".yaml")
        self.logger.info(f"Backing up metadata to: {savedir}")
        return backup_metadata_to_filepath(metadata, savedir)

    def get_blake2_str(
        self, file_input: Path
    ) -> str:  # TODO: Figure out how df file types work
        self.logger.info("Setting Blake2b as the hash method of choice")
        hasher = hashlib.blake2b
        hash_object = hasher()
        self.logger.info("Created Hash object and initialized hash.")
        if isinstance(file_input, Path):
            f = open(file_input, "rb")
            buf = f.read(65536)
            # self.logger.info(buf)
            while len(buf) > 0:
                hash_object.update(buf)
                buf = f.read(65536)
            return base64.urlsafe_b64encode(hash_object.digest()).decode()
        self.logger.error("Failed to hash file")
        raise Exception("ErrorHashingFile")  # I am really sorry about this

    def backup_processed_text(
        self, text: str, hash: str, metadata: dict, backupdir: Path
    ) -> None:
        savestring = create_markdown_string(
            text, metadata, include_previous_metadata=False
        )
        backuppath = backupdir / Path(hash + ".md")
        # Seems slow to check every time a file is backed up
        backuppath.parent.mkdir(parents=True, exist_ok=True)
        if backuppath.exists():
            backuppath.unlink(missing_ok=True)
        # FIXME: We should probably come up with a better backup protocol then doing everything with hashes
        if backuppath.is_file():
            backuppath.unlink(missing_ok=True)
        with open(backuppath, "w") as text_file:
            text_file.write(savestring)

    def download_file_to_path(self, url: str, savepath: Path) -> Path:
        savepath.parent.mkdir(exist_ok=True, parents=True)
        self.logger.info(f"Downloading file to dir: {savepath}")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(savepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    # if chunk:
                    f.write(chunk)
        return savepath

    # TODO : Get types for temporary file
    def download_file_to_tmpfile(self, url: str) -> Any:
        self.logger.info(f"Downloading file to temporary file")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with TemporaryFile("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    # if chunk:
                    f.write(chunk)
                return f

    # S3 Stuff Below this point

    def hash_to_fileid(self, hash: str) -> str:
        return self.s3_raw_directory + hash

    async def generate_local_filepath_from_hash_async(
        self, hash: str, ensure_network: bool = True, download_local: bool = True
    ) -> Optional[Path]:
        return await asyncio.to_thread(
            self.generate_local_filepath_from_hash, hash, ensure_network, download_local
        )

    def generate_local_filepath_from_hash(
        self, hash: str, ensure_network: bool = True, download_local: bool = True
    ) -> Optional[Path]:
        local_filepath = self.get_default_filepath_from_hash(hash)
        if local_filepath.is_file():
            if ensure_network:
                if not self.does_hash_exist_s3(hash):
                    self.push_raw_file_to_s3(local_filepath, hash)
            return local_filepath
        # TODO:  Remove assurance on s3 functionality now that other function exists
        if not download_local:
            return None
        s3_hash_name = self.s3_raw_directory + hash
        return self.download_s3_file_to_path(s3_hash_name, local_filepath)

    def generate_s3_uri_from_hash(
        self, hash: str, upload_local: bool = True
    ) -> Optional[str]:
        fileid = self.hash_to_fileid(hash)
        if self.does_file_exist_s3(fileid):
            return self.generate_s3_uri(fileid)
        if upload_local:
            local_filepath = self.get_default_filepath_from_hash(hash)
            if local_filepath.is_file():
                self.push_raw_file_to_s3(local_filepath, hash)
                return self.generate_s3_uri(fileid)

    def download_s3_file_to_path(
        self, file_name: str, file_path: Path, bucket: Optional[str] = None
    ) -> Optional[Path]:
        if bucket is None:
            bucket = self.bucket
        if file_path.is_file():
            raise Exception("File Already Present at Path, not downloading")
        try:
            self.s3.download_file(bucket, file_name, str(file_path))
            return file_path
        except Exception as e:
            self.logger.error(
                f"Something whent wrong when downloading s3, is the file missing, raised error {e}"
            )
            return None

    def download_file_from_s3_url(
        self, s3_url: str, local_path: Path
    ) -> Optional[Path]:
        domain = urlparse(s3_url).hostname
        s3_key = urlparse(s3_url).path
        if domain is None or s3_key is None:
            raise ValueError("Invalid URL")
        s3_bucket = domain.split(".")[0]
        return self.download_s3_file_to_path(
            file_name=s3_key, file_path=local_path, bucket=s3_bucket
        )

    def generate_s3_uri(
        self,
        file_name: str,
        bucket: Optional[str] = None,
        s3_endpoint: Optional[str] = None,
    ) -> str:
        if s3_endpoint is None:
            s3_endpoint = self.endpoint

        if bucket is None:
            bucket = self.bucket

        # Remove any trailing slashes from the S3 endpoint
        s3_endpoint = s3_endpoint.rstrip("/")

        # Extract the base endpoint (e.g., sfo3.digitaloceanspaces.com)
        base_endpoint = s3_endpoint.split("//")[-1]

        # Construct the S3 URI
        s3_uri = f"https://{bucket}.{base_endpoint}/{file_name}"

        return s3_uri

    def does_file_exist_s3(self, key: str, bucket: Optional[str] = None) -> bool:
        if bucket is None:
            bucket = self.bucket

        try:
            self.s3.get_object(
                Bucket=bucket,
                Key=key,
            )
            return True
        except self.s3.exceptions.NoSuchKey:
            return False

    def does_hash_exist_s3(self, hash: str, bucket: Optional[str] = None) -> bool:
        if bucket is None:
            bucket = self.bucket
        fileid = self.hash_to_fileid(hash)
        return self.does_file_exist_s3(fileid, bucket)

    def download_file_to_file_in_tmpdir(
        self, url: str
    ) -> Any:  # TODO : Get types for temporary file
        savedir = self.tmpdir / Path(rand_string())
        return self.download_file_to_path(url, savedir)

    def push_file_to_s3(
        self, filepath: Path, file_upload_name: str, bucket: Optional[str] = None
    ) -> str:
        if bucket is None:
            bucket = self.bucket
        return self.s3.upload_file(str(filepath), bucket, file_upload_name)

    def push_raw_file_to_s3_novalid(self, filepath: Path, hash: str) -> str:
        if not filepath.is_file():
            raise Exception("File does not exist")
        filename = self.hash_to_fileid(hash)
        return self.push_file_to_s3(filepath, filename)

    def push_raw_file_to_s3(
        self, filepath: Path, hash: Optional[str] = None
    ) -> Tuple[bool, str]:
        if not filepath.is_file():
            raise Exception("File does not exist")
        actual_hash = self.get_blake2_str(filepath)
        if hash is not None and actual_hash != hash:
            raise Exception("Hashes did not match, erroring out")

        if not self.does_hash_exist_s3(actual_hash):
            return False, self.push_raw_file_to_s3_novalid(filepath, actual_hash)
        return True, self.hash_to_fileid(actual_hash)
