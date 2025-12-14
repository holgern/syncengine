Storage Protocols
=================

SyncEngine is designed to be storage-agnostic through a protocol-based architecture. This document explains how to implement custom storage backends.

Protocol Overview
-----------------

SyncEngine uses Python's ``typing.Protocol`` for structural subtyping. This means any class that implements the required methods will work with SyncEngine without needing to inherit from a base class.

Core protocols:

* ``StorageClientProtocol``: Interface for storage operations (upload, download, delete)
* ``FileEntryProtocol``: Interface for file/folder metadata
* ``FileEntriesManagerProtocol``: Interface for managing file collections

StorageClientProtocol
---------------------

The main interface for storage backends.

Required Methods
~~~~~~~~~~~~~~~~

upload_file()
^^^^^^^^^^^^^

Upload a file to storage:

.. code-block:: python

   def upload_file(
       self,
       file_path: Path,
       relative_path: str,
       storage_id: int = 0,
       chunk_size: int = 5242880,
       use_multipart_threshold: int = 52428800,
       progress_callback: Optional[Callable[[int, int], None]] = None
   ) -> Any:
       """Upload a file to storage.

       Args:
           file_path: Local path to file to upload
           relative_path: Path in storage (preserves directory structure)
           storage_id: Storage/workspace identifier (0 for default)
           chunk_size: Size of upload chunks in bytes
           use_multipart_threshold: File size to trigger multipart upload
           progress_callback: Called with (bytes_uploaded, total_bytes)

       Returns:
           Upload result (implementation-specific)
       """
       pass

download_file()
^^^^^^^^^^^^^^^

Download a file from storage:

.. code-block:: python

   def download_file(
       self,
       hash_value: str,
       output_path: Path,
       progress_callback: Optional[Callable[[int, int], None]] = None
   ) -> Path:
       """Download a file from storage.

       Args:
           hash_value: Content hash of the file
           output_path: Local path where file should be saved
           progress_callback: Called with (bytes_downloaded, total_bytes)

       Returns:
           Path where file was saved
       """
       pass

delete_file_entries()
^^^^^^^^^^^^^^^^^^^^^

Delete files from storage:

.. code-block:: python

   def delete_file_entries(
       self,
       entry_ids: list[int],
       delete_forever: bool = False
   ) -> Any:
       """Delete file entries from storage.

       Args:
           entry_ids: List of entry IDs to delete
           delete_forever: If True, permanently delete; if False, move to trash

       Returns:
           Delete result (implementation-specific)
       """
       pass

create_folder()
^^^^^^^^^^^^^^^

Create a folder in storage:

.. code-block:: python

   def create_folder(
       self,
       name: str,
       parent_id: Optional[int] = None,
       storage_id: int = 0
   ) -> dict[str, Any]:
       """Create a folder in storage.

       Args:
           name: Folder name (can include path separators for nested folders)
           parent_id: Parent folder ID (None for root)
           storage_id: Storage/workspace identifier

       Returns:
           Dictionary with 'status' and 'id' keys
       """
       pass

resolve_path_to_id()
^^^^^^^^^^^^^^^^^^^^

Resolve a path to an entry ID:

.. code-block:: python

   def resolve_path_to_id(
       self,
       path: str,
       storage_id: int = 0
   ) -> Optional[int]:
       """Resolve a path to an entry ID.

       Args:
           path: Path to resolve
           storage_id: Storage/workspace identifier

       Returns:
           Entry ID if found, None otherwise
       """
       pass

rename_entry()
^^^^^^^^^^^^^^

Rename/move an entry:

.. code-block:: python

   def rename_entry(
       self,
       entry_id: int,
       new_name: str,
       new_parent_id: Optional[int] = None
   ) -> Any:
       """Rename or move an entry.

       Args:
           entry_id: Entry to rename/move
           new_name: New name
           new_parent_id: New parent folder ID (for moves)

       Returns:
           Rename result (implementation-specific)
       """
       pass

FileEntryProtocol
-----------------

Interface for file/folder metadata.

Required Properties
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from typing import Protocol, Optional

   class FileEntryProtocol(Protocol):
       @property
       def id(self) -> int:
           """Unique identifier (persists across renames)."""
           ...

       @property
       def type(self) -> str:
           """Entry type: 'file' or 'folder'."""
           ...

       @property
       def file_size(self) -> int:
           """File size in bytes (0 for folders)."""
           ...

       @property
       def hash(self) -> str:
           """Content hash (e.g., MD5, SHA256)."""
           ...

       @property
       def name(self) -> str:
           """File or folder name."""
           ...

       @property
       def updated_at(self) -> Optional[str]:
           """ISO timestamp of last modification."""
           ...

Example Implementation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class MyFileEntry:
       def __init__(self, data: dict):
           self._data = data

       @property
       def id(self) -> int:
           return self._data['id']

       @property
       def type(self) -> str:
           return self._data['type']

       @property
       def file_size(self) -> int:
           return self._data.get('size', 0)

       @property
       def hash(self) -> str:
           return self._data.get('hash', '')

       @property
       def name(self) -> str:
           return self._data['name']

       @property
       def updated_at(self) -> Optional[str]:
           return self._data.get('updated_at')

FileEntriesManagerProtocol
---------------------------

Interface for managing collections of file entries.

Required Methods
~~~~~~~~~~~~~~~~

get_all_entries()
^^^^^^^^^^^^^^^^^

Get all entries in storage:

.. code-block:: python

   def get_all_entries(self) -> Iterator[FileEntryProtocol]:
       """Get all file entries.

       Yields:
           File entries one at a time
       """
       pass

refresh()
^^^^^^^^^

Refresh the entry cache:

.. code-block:: python

   def refresh(self) -> None:
       """Refresh the internal cache of entries."""
       pass

get_entry_by_id()
^^^^^^^^^^^^^^^^^

Get an entry by ID:

.. code-block:: python

   def get_entry_by_id(self, entry_id: int) -> Optional[FileEntryProtocol]:
       """Get an entry by its ID.

       Args:
           entry_id: Entry ID to look up

       Returns:
           File entry if found, None otherwise
       """
       pass

Implementing a Storage Backend
-------------------------------

Here's a complete example of implementing a custom storage backend:

Example: S3 Storage Backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import boto3
   from pathlib import Path
   from typing import Any, Callable, Iterator, Optional
   from syncengine.protocols import (
       StorageClientProtocol,
       FileEntryProtocol,
       FileEntriesManagerProtocol
   )

   class S3FileEntry:
       """File entry for S3 objects."""

       def __init__(self, obj: dict, bucket: str):
           self._obj = obj
           self._bucket = bucket

       @property
       def id(self) -> int:
           # Use hash of key as ID
           return hash(self._obj['Key'])

       @property
       def type(self) -> str:
           return 'folder' if self._obj['Key'].endswith('/') else 'file'

       @property
       def file_size(self) -> int:
           return self._obj.get('Size', 0)

       @property
       def hash(self) -> str:
           # S3 provides ETag which is often the MD5 hash
           return self._obj.get('ETag', '').strip('"')

       @property
       def name(self) -> str:
           return self._obj['Key'].split('/')[-1]

       @property
       def updated_at(self) -> Optional[str]:
           dt = self._obj.get('LastModified')
           return dt.isoformat() if dt else None

   class S3EntriesManager:
       """Manages S3 file entries."""

       def __init__(self, client: 'S3StorageClient', bucket: str, prefix: str = ''):
           self.client = client
           self.bucket = bucket
           self.prefix = prefix
           self._entries: list[S3FileEntry] = []
           self.refresh()

       def refresh(self) -> None:
           """Refresh entries from S3."""
           self._entries = []
           paginator = self.client.s3_client.get_paginator('list_objects_v2')

           for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
               for obj in page.get('Contents', []):
                   self._entries.append(S3FileEntry(obj, self.bucket))

       def get_all_entries(self) -> Iterator[FileEntryProtocol]:
           """Get all entries."""
           yield from self._entries

       def get_entry_by_id(self, entry_id: int) -> Optional[FileEntryProtocol]:
           """Get entry by ID."""
           for entry in self._entries:
               if entry.id == entry_id:
                   return entry
           return None

   class S3StorageClient:
       """S3 storage backend for SyncEngine."""

       def __init__(self, bucket: str, prefix: str = '', **kwargs):
           self.bucket = bucket
           self.prefix = prefix
           self.s3_client = boto3.client('s3', **kwargs)

       def upload_file(
           self,
           file_path: Path,
           relative_path: str,
           storage_id: int = 0,
           chunk_size: int = 5242880,
           use_multipart_threshold: int = 52428800,
           progress_callback: Optional[Callable[[int, int], None]] = None
       ) -> Any:
           """Upload file to S3."""
           key = f"{self.prefix}/{relative_path}".lstrip('/')
           file_size = file_path.stat().st_size

           # Progress callback wrapper
           def s3_progress(bytes_transferred):
               if progress_callback:
                   progress_callback(bytes_transferred, file_size)

           # Upload file
           self.s3_client.upload_file(
               str(file_path),
               self.bucket,
               key,
               Callback=s3_progress
           )

           return {'key': key, 'bucket': self.bucket}

       def download_file(
           self,
           hash_value: str,
           output_path: Path,
           progress_callback: Optional[Callable[[int, int], None]] = None
       ) -> Path:
           """Download file from S3."""
           # In real implementation, you'd need to map hash to S3 key
           # This is simplified for example purposes
           key = self._hash_to_key(hash_value)

           # Get file size
           response = self.s3_client.head_object(Bucket=self.bucket, Key=key)
           file_size = response['ContentLength']

           # Progress callback wrapper
           def s3_progress(bytes_transferred):
               if progress_callback:
                   progress_callback(bytes_transferred, file_size)

           # Download file
           self.s3_client.download_file(
               self.bucket,
               key,
               str(output_path),
               Callback=s3_progress
           )

           return output_path

       def delete_file_entries(
           self,
           entry_ids: list[int],
           delete_forever: bool = False
       ) -> Any:
           """Delete files from S3."""
           # Map IDs to keys
           keys = [self._id_to_key(entry_id) for entry_id in entry_ids]

           # Delete objects
           self.s3_client.delete_objects(
               Bucket=self.bucket,
               Delete={
                   'Objects': [{'Key': key} for key in keys]
               }
           )

           return {'deleted': len(keys)}

       def create_folder(
           self,
           name: str,
           parent_id: Optional[int] = None,
           storage_id: int = 0
       ) -> dict[str, Any]:
           """Create folder in S3 (zero-byte object with trailing slash)."""
           key = f"{self.prefix}/{name}/".lstrip('/')

           self.s3_client.put_object(
               Bucket=self.bucket,
               Key=key,
               Body=b''
           )

           return {'status': 'created', 'id': hash(key)}

       def resolve_path_to_id(
           self,
           path: str,
           storage_id: int = 0
       ) -> Optional[int]:
           """Resolve path to ID."""
           key = f"{self.prefix}/{path}".lstrip('/')

           try:
               self.s3_client.head_object(Bucket=self.bucket, Key=key)
               return hash(key)
           except self.s3_client.exceptions.NoSuchKey:
               return None

       def rename_entry(
           self,
           entry_id: int,
           new_name: str,
           new_parent_id: Optional[int] = None
       ) -> Any:
           """Rename/move entry in S3."""
           old_key = self._id_to_key(entry_id)
           new_key = f"{self.prefix}/{new_name}".lstrip('/')

           # Copy to new location
           self.s3_client.copy_object(
               Bucket=self.bucket,
               CopySource={'Bucket': self.bucket, 'Key': old_key},
               Key=new_key
           )

           # Delete old location
           self.s3_client.delete_object(Bucket=self.bucket, Key=old_key)

           return {'old_key': old_key, 'new_key': new_key}

       def _hash_to_key(self, hash_value: str) -> str:
           """Map hash to S3 key (implementation-specific)."""
           # In real implementation, maintain a hash->key mapping
           raise NotImplementedError()

       def _id_to_key(self, entry_id: int) -> str:
           """Map ID to S3 key (implementation-specific)."""
           # In real implementation, maintain an ID->key mapping
           raise NotImplementedError()

   # Usage
   from syncengine import SyncEngine, SyncPair, SyncMode

   # Create S3 client
   s3_client = S3StorageClient(
       bucket='my-bucket',
       prefix='sync-folder',
       region_name='us-west-2'
   )

   # Create entries manager factory
   def create_entries_manager(client, storage_id):
       return S3EntriesManager(client, 'my-bucket', 'sync-folder')

   # Create sync engine
   engine = SyncEngine(
       client=s3_client,
       entries_manager_factory=create_entries_manager
   )

   # Create sync pair
   pair = SyncPair(
       source_root="/home/user/docs",
       destination_root="",
       source_client=local_client,
       destination_client=s3_client,
       mode=SyncMode.SOURCE_TO_DESTINATION
   )

   # Sync
   stats = engine.sync_pair(pair)

Testing Your Implementation
----------------------------

SyncEngine includes test utilities to verify your storage backend:

.. code-block:: python

   from syncengine.testing import StorageClientTestSuite

   class TestS3Client(StorageClientTestSuite):
       def create_client(self):
           """Create a client instance for testing."""
           return S3StorageClient(
               bucket='test-bucket',
               region_name='us-west-2'
           )

       def create_entries_manager(self, client, storage_id):
           """Create an entries manager for testing."""
           return S3EntriesManager(client, 'test-bucket')

   # Run tests
   pytest.main([__file__])

Best Practices
--------------

Error Handling
~~~~~~~~~~~~~~

* Implement proper error handling and retries
* Raise meaningful exceptions
* Log errors for debugging

.. code-block:: python

   def upload_file(self, file_path: Path, relative_path: str, **kwargs):
       try:
           # Upload logic
           pass
       except ConnectionError as e:
           logger.error(f"Connection error uploading {file_path}: {e}")
           raise
       except Exception as e:
           logger.error(f"Error uploading {file_path}: {e}")
           raise

Progress Callbacks
~~~~~~~~~~~~~~~~~~

* Always call progress callbacks if provided
* Report accurate progress
* Call with final values on completion

.. code-block:: python

   def upload_file(self, file_path: Path, relative_path: str,
                   progress_callback=None, **kwargs):
       file_size = file_path.stat().st_size
       bytes_uploaded = 0

       # Upload in chunks
       with open(file_path, 'rb') as f:
           while chunk := f.read(8192):
               # Upload chunk
               upload_chunk(chunk)
               bytes_uploaded += len(chunk)

               if progress_callback:
                   progress_callback(bytes_uploaded, file_size)

       # Ensure final callback
       if progress_callback:
           progress_callback(file_size, file_size)

Content Hashing
~~~~~~~~~~~~~~~

* Use consistent hashing algorithm (MD5, SHA256)
* Compute hashes efficiently
* Cache hashes when possible

.. code-block:: python

   import hashlib

   def compute_hash(file_path: Path) -> str:
       """Compute MD5 hash of file."""
       hasher = hashlib.md5()
       with open(file_path, 'rb') as f:
           for chunk in iter(lambda: f.read(8192), b''):
               hasher.update(chunk)
       return hasher.hexdigest()

Caching
~~~~~~~

* Cache file listings when possible
* Implement efficient refresh mechanisms
* Invalidate cache when needed

.. code-block:: python

   class CachedEntriesManager:
       def __init__(self, client):
           self.client = client
           self._cache = {}
           self._cache_time = None
           self._cache_ttl = 300  # 5 minutes

       def get_all_entries(self):
           now = time.time()
           if (self._cache_time is None or
               now - self._cache_time > self._cache_ttl):
               self.refresh()

           yield from self._cache.values()

       def refresh(self):
           self._cache = {}
           # Fetch entries from storage
           for entry in self.client.list_entries():
               self._cache[entry.id] = entry
           self._cache_time = time.time()

Next Steps
----------

* :doc:`examples` - See complete examples
* :doc:`api_reference` - Detailed API documentation
* Review existing implementations (LocalStorageClient, etc.)
