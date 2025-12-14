Benchmarks
==========

SyncEngine includes comprehensive benchmarks to measure performance across different sync modes and scenarios.

Overview
--------

The benchmark suite tests:

* All five sync modes
* Various file sizes (small, medium, large)
* Different numbers of files (few, many, mixed)
* Common operations (add, modify, delete, rename)
* Edge cases (conflicts, partial syncs, interrupted syncs)

Running Benchmarks
------------------

Basic Usage
~~~~~~~~~~~

Run all benchmarks:

.. code-block:: bash

   python benchmarks/run_benchmarks.py

Run specific benchmark:

.. code-block:: bash

   python benchmarks/benchmark_two_way.py

Run with custom parameters:

.. code-block:: bash

   python benchmarks/run_benchmarks.py --num-files 1000 --file-size 1MB

Benchmark Modules
-----------------

benchmark_two_way.py
~~~~~~~~~~~~~~~~~~~~

Tests TWO_WAY sync mode:

* Bidirectional file changes
* Conflict detection and resolution
* Rename/move detection
* Delete propagation both ways

Example results::

   TWO_WAY Sync Benchmark
   =====================
   Files: 100 (avg size: 1MB)

   Initial sync:
     Time: 2.34s
     Uploaded: 100 files (100MB)
     Downloaded: 0 files

   Modify 10 files at source:
     Time: 0.45s
     Uploaded: 10 files (10MB)
     Downloaded: 0 files

   Modify 10 files at destination:
     Time: 0.47s
     Uploaded: 0 files
     Downloaded: 10 files (10MB)

   Modify 5 files at both sides (conflicts):
     Time: 0.28s
     Conflicts resolved: 5
     Actions taken: 5 uploads

benchmark_source_to_destination.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tests SOURCE_TO_DESTINATION sync mode:

* One-way mirroring
* Destination changes ignored
* Source deletions propagated

Example results::

   SOURCE_TO_DESTINATION Sync Benchmark
   ===================================
   Files: 100 (avg size: 1MB)

   Initial sync:
     Time: 2.31s
     Uploaded: 100 files (100MB)

   Add 10 files at source:
     Time: 0.43s
     Uploaded: 10 files (10MB)

   Add 10 files at destination:
     Time: 0.19s
     Deleted: 10 files (not in source)

   Delete 10 files at source:
     Time: 0.15s
     Deleted: 10 files (at destination)

benchmark_source_backup.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tests SOURCE_BACKUP sync mode:

* Upload-only backup
* Source deletions not propagated
* Destination grows over time

Example results::

   SOURCE_BACKUP Sync Benchmark
   ============================
   Files: 100 (avg size: 1MB)

   Initial sync:
     Time: 2.35s
     Uploaded: 100 files (100MB)

   Delete 10 files at source:
     Time: 0.05s
     Deleted: 0 files (backup preserved)

   Modify 10 files at source:
     Time: 0.44s
     Uploaded: 10 files (10MB)

   Destination size after deletes:
     Files: 100 (backup preserved)

benchmark_destination_to_source.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tests DESTINATION_TO_SOURCE sync mode:

* One-way mirroring from destination
* Source changes ignored
* Destination deletions propagated

Example results::

   DESTINATION_TO_SOURCE Sync Benchmark
   ===================================
   Files: 100 (avg size: 1MB)

   Initial sync:
     Time: 2.33s
     Downloaded: 100 files (100MB)

   Add 10 files at destination:
     Time: 0.42s
     Downloaded: 10 files (10MB)

   Add 10 files at source:
     Time: 0.18s
     Deleted: 10 files (not in destination)

benchmark_destination_backup.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tests DESTINATION_BACKUP sync mode:

* Download-only backup
* Destination deletions not propagated
* Source grows over time

Example results::

   DESTINATION_BACKUP Sync Benchmark
   ================================
   Files: 100 (avg size: 1MB)

   Initial sync:
     Time: 2.36s
     Downloaded: 100 files (100MB)

   Delete 10 files at destination:
     Time: 0.05s
     Deleted: 0 files (backup preserved)

   Modify 10 files at destination:
     Time: 0.45s
     Downloaded: 10 files (10MB)

benchmark_sync_modes.py
~~~~~~~~~~~~~~~~~~~~~~~

Compares all sync modes side-by-side:

* Same test data for all modes
* Measures time and operations
* Highlights mode differences

Example results::

   Sync Modes Comparison
   =====================
   Test: 100 files (1MB each), modify 10 at source

   TWO_WAY:              0.45s (10 uploads)
   SOURCE_TO_DEST:       0.44s (10 uploads)
   SOURCE_BACKUP:        0.46s (10 uploads)
   DEST_TO_SOURCE:       0.05s (0 operations)
   DEST_BACKUP:          0.05s (0 operations)

   Test: 100 files (1MB each), modify 10 at destination

   TWO_WAY:              0.47s (10 downloads)
   SOURCE_TO_DEST:       0.18s (10 deletes)
   SOURCE_BACKUP:        0.48s (10 downloads)
   DEST_TO_SOURCE:       0.46s (10 downloads)
   DEST_BACKUP:          0.47s (10 downloads)

Performance Metrics
-------------------

Key Metrics
~~~~~~~~~~~

The benchmarks measure:

1. **Time**: Wall clock time for operations
2. **Throughput**: MB/s for uploads/downloads
3. **Operations**: Number of file operations
4. **Efficiency**: Time per file operation

Example metrics output::

   Performance Metrics
   ===================
   Total time: 5.23s

   Operations:
     Uploads: 100 (2.34s, 42.7 MB/s)
     Downloads: 50 (1.12s, 44.6 MB/s)
     Deletes: 20 (0.08s, 250 ops/s)
     Renames: 10 (0.05s, 200 ops/s)

   Efficiency:
     Time per upload: 23.4ms
     Time per download: 22.4ms
     Time per delete: 4ms
     Time per rename: 5ms

Scaling Tests
~~~~~~~~~~~~~

Test performance with different scales:

**Small Files (many files, small size)**

.. code-block:: bash

   python benchmarks/run_benchmarks.py --num-files 10000 --file-size 10KB

Expected results::

   Small Files Test
   ================
   Files: 10,000 (10KB each)
   Total size: 100MB

   Initial sync: 8.45s (11.8 MB/s)
   Incremental sync (100 changes): 0.89s

**Large Files (few files, large size)**

.. code-block:: bash

   python benchmarks/run_benchmarks.py --num-files 10 --file-size 100MB

Expected results::

   Large Files Test
   ================
   Files: 10 (100MB each)
   Total size: 1GB

   Initial sync: 23.4s (42.7 MB/s)
   Incremental sync (1 change): 2.3s

**Mixed Files (realistic mix)**

.. code-block:: bash

   python benchmarks/run_benchmarks.py --mixed

Expected results::

   Mixed Files Test
   ================
   Files: 1,000 (10KB to 10MB, avg 500KB)
   Total size: 500MB

   Initial sync: 12.3s (40.7 MB/s)
   Incremental sync (50 changes): 1.2s

Concurrency Tests
~~~~~~~~~~~~~~~~~

Test different concurrency levels:

.. code-block:: bash

   python benchmarks/benchmark_concurrency.py

Results::

   Concurrency Test
   ================
   Files: 100 (1MB each)

   Transfers=1:   4.56s (21.9 MB/s)
   Transfers=3:   2.34s (42.7 MB/s)
   Transfers=5:   1.89s (52.9 MB/s)
   Transfers=10:  1.92s (52.1 MB/s)
   Transfers=20:  2.01s (49.8 MB/s)

   Optimal concurrency: 5-10 transfers

Interpretation
--------------

Understanding Results
~~~~~~~~~~~~~~~~~~~~~

**Good Performance**

* Upload/download: 40-60 MB/s (local/fast network)
* Small files: 100-500 ops/s
* Large files: 40-60 MB/s
* Incremental sync: <1s for typical changes

**Poor Performance**

* Upload/download: <10 MB/s
* Small files: <50 ops/s
* Large files: <20 MB/s
* Incremental sync: >5s for small changes

**Performance Factors**

1. **Network**: Biggest factor for remote storage
2. **Disk I/O**: Important for local operations
3. **File count**: Many small files slower than few large files
4. **Concurrency**: Optimal level depends on network/disk
5. **State management**: Enabled = faster incremental syncs

Optimization Tips
~~~~~~~~~~~~~~~~~

Based on benchmark results:

1. **Use state management** for incremental syncs (10-100x faster)
2. **Optimize concurrency** for your network (test 3-10 transfers)
3. **Use ignore patterns** to skip unnecessary files
4. **Choose appropriate sync mode** (one-way modes faster than TWO_WAY)
5. **Batch operations** when possible
6. **Monitor metrics** to identify bottlenecks

Continuous Benchmarking
-----------------------

Integration with CI/CD
~~~~~~~~~~~~~~~~~~~~~~

Run benchmarks in CI to detect performance regressions:

.. code-block:: yaml

   # .github/workflows/benchmarks.yml
   name: Benchmarks

   on:
     pull_request:
       branches: [main]

   jobs:
     benchmark:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2

         - name: Set up Python
           uses: actions/setup-python@v2
           with:
             python-version: 3.9

         - name: Install dependencies
           run: |
             pip install -e .
             pip install pytest-benchmark

         - name: Run benchmarks
           run: |
             python benchmarks/run_benchmarks.py --output results.json

         - name: Compare results
           run: |
             python benchmarks/compare_results.py \
               --baseline baseline.json \
               --current results.json \
               --threshold 10  # Fail if >10% regression

Custom Benchmarks
-----------------

Creating Custom Benchmarks
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create your own benchmarks for specific use cases:

.. code-block:: python

   import time
   from pathlib import Path
   from syncengine import SyncEngine, SyncPair, SyncMode
   from benchmarks.test_utils import create_test_files, measure_time

   def benchmark_custom_scenario():
       """Custom benchmark for specific scenario."""

       # Setup
       source_dir = Path("/tmp/bench_source")
       dest_dir = Path("/tmp/bench_dest")

       # Create test data
       create_test_files(
           source_dir,
           num_files=100,
           file_size=1024*1024  # 1MB
       )

       # Create sync engine
       engine = SyncEngine(
           client=dest_client,
           entries_manager_factory=create_entries_manager
       )

       pair = SyncPair(
           source_root=str(source_dir),
           destination_root=str(dest_dir),
           source_client=source_client,
           destination_client=dest_client,
           mode=SyncMode.TWO_WAY
       )

       # Benchmark
       with measure_time() as timer:
           stats = engine.sync_pair(pair)

       # Report
       print(f"Time: {timer.elapsed:.2f}s")
       print(f"Throughput: {100 / timer.elapsed:.1f} files/s")
       print(f"Stats: {stats}")

   if __name__ == "__main__":
       benchmark_custom_scenario()

Benchmark Best Practices
~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Isolate tests**: Use fresh directories for each test
2. **Warm up**: Run once before measuring
3. **Repeat**: Run multiple times and average
4. **Clean up**: Remove test files after benchmarks
5. **Consistent environment**: Same hardware, network conditions
6. **Measure what matters**: Focus on real-world scenarios

Next Steps
----------

* Run benchmarks: ``python benchmarks/run_benchmarks.py``
* See :doc:`examples` for usage examples
* Read :doc:`api_reference` for optimization options
