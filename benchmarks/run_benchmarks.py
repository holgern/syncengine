#!/usr/bin/env python3
"""
Benchmark runner for syncengine sync modes.

This script discovers and runs all benchmark scripts in the benchmarks directory,
captures their output, detects errors, and provides a summary report.
"""

import subprocess
import sys
import time
from pathlib import Path


class BenchmarkResult:
    """Result of running a single benchmark."""

    def __init__(
        self,
        name: str,
        success: bool,
        duration: float,
        output: str = "",
        error: str = "",
        exit_code: int = 0,
    ):
        """Initialize benchmark result.

        Args:
            name: Name of the benchmark
            success: Whether the benchmark passed
            duration: Execution time in seconds
            output: Standard output from the benchmark
            error: Standard error from the benchmark
            exit_code: Process exit code
        """
        self.name = name
        self.success = success
        self.duration = duration
        self.output = output
        self.error = error
        self.exit_code = exit_code


class BenchmarkRunner:
    """Runner for executing benchmark scripts."""

    def __init__(self, benchmarks_dir: Path, verbose: bool = False):
        """Initialize the benchmark runner.

        Args:
            benchmarks_dir: Directory containing benchmark scripts
            verbose: Whether to print verbose output
        """
        self.benchmarks_dir = benchmarks_dir
        self.verbose = verbose
        self.results: list[BenchmarkResult] = []

    def discover_benchmarks(self) -> list[Path]:
        """Discover all benchmark scripts in the benchmarks directory.

        Returns:
            List of paths to benchmark scripts
        """
        benchmarks = []
        for file_path in sorted(self.benchmarks_dir.glob("benchmark_*.py")):
            if file_path.name != "benchmark_sync_modes.py":  # Run this last
                benchmarks.append(file_path)

        # Add benchmark_sync_modes.py at the end (it runs all modes together)
        sync_modes_bench = self.benchmarks_dir / "benchmark_sync_modes.py"
        if sync_modes_bench.exists():
            benchmarks.append(sync_modes_bench)

        return benchmarks

    def run_benchmark(self, benchmark_path: Path) -> BenchmarkResult:
        """Run a single benchmark script.

        Args:
            benchmark_path: Path to the benchmark script

        Returns:
            BenchmarkResult containing execution results
        """
        name = benchmark_path.stem.replace("benchmark_", "").replace("_", " ").title()

        if self.verbose:
            print(f"\n{'=' * 80}")
            print(f"Running: {name}")
            print(f"Script: {benchmark_path.name}")
            print("=" * 80)

        start_time = time.time()

        try:
            # Run the benchmark script
            process = subprocess.Popen(
                [sys.executable, str(benchmark_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=benchmark_path.parent.parent,  # Run from syncengine root
            )

            # Capture output
            stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout
            duration = time.time() - start_time

            # Check for success
            success = process.returncode == 0

            if self.verbose:
                if stdout:
                    print(stdout)
                if stderr and not success:
                    print(f"\n[STDERR]\n{stderr}", file=sys.stderr)

            return BenchmarkResult(
                name=name,
                success=success,
                duration=duration,
                output=stdout,
                error=stderr,
                exit_code=process.returncode,
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return BenchmarkResult(
                name=name,
                success=False,
                duration=duration,
                error="Benchmark timed out after 5 minutes",
                exit_code=-1,
            )
        except Exception as e:
            duration = time.time() - start_time
            return BenchmarkResult(
                name=name,
                success=False,
                duration=duration,
                error=f"Exception during execution: {e}",
                exit_code=-1,
            )

    def run_all(self) -> None:
        """Run all discovered benchmarks."""
        benchmarks = self.discover_benchmarks()

        if not benchmarks:
            print("[WARN] No benchmark scripts found!")
            return

        print("\n" + "=" * 80)
        print("SYNCENGINE BENCHMARK RUNNER")
        print("=" * 80)
        print(f"\nDiscovered {len(benchmarks)} benchmark(s)")
        print("-" * 80)

        for benchmark in benchmarks:
            result = self.run_benchmark(benchmark)
            self.results.append(result)

            # Print quick status
            if not self.verbose:
                status = "✓" if result.success else "✗"
                print(
                    f"{status} {result.name:<40} "
                    f"[{result.duration:.2f}s] "
                    f"{'PASS' if result.success else 'FAIL'}"
                )

    def print_summary(self) -> None:
        """Print summary of all benchmark results."""
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed
        total_time = sum(r.duration for r in self.results)

        print(f"\nTotal benchmarks: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total time: {total_time:.2f}s")

        if failed > 0:
            print("\n" + "-" * 80)
            print("FAILED BENCHMARKS")
            print("-" * 80)
            for result in self.results:
                if not result.success:
                    print(f"\n[✗] {result.name}")
                    print(f"    Exit code: {result.exit_code}")
                    print(f"    Duration: {result.duration:.2f}s")
                    if result.error:
                        print(f"    Error: {result.error}")
                    # Print last few lines of output for context
                    if result.output:
                        lines = result.output.strip().split("\n")
                        last_lines = lines[-10:] if len(lines) > 10 else lines
                        print("    Last output lines:")
                        for line in last_lines:
                            print(f"      {line}")

        print("\n" + "=" * 80)
        if failed == 0:
            print("[SUCCESS] All benchmarks passed!")
        else:
            print(f"[FAILURE] {failed} benchmark(s) failed")
        print("=" * 80)

    def get_exit_code(self) -> int:
        """Get exit code based on benchmark results.

        Returns:
            0 if all passed, 1 if any failed
        """
        return 0 if all(r.success for r in self.results) else 1


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run all syncengine benchmark scripts")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print verbose output from benchmarks",
    )
    parser.add_argument(
        "-b",
        "--benchmark",
        type=str,
        help="Run specific benchmark (e.g., 'two_way', 'source_backup')",
    )

    args = parser.parse_args()

    # Determine benchmarks directory
    benchmarks_dir = Path(__file__).parent

    runner = BenchmarkRunner(benchmarks_dir, verbose=args.verbose)

    # Run specific benchmark or all
    if args.benchmark:
        benchmark_file = benchmarks_dir / f"benchmark_{args.benchmark}.py"
        if not benchmark_file.exists():
            print(f"[ERROR] Benchmark not found: {benchmark_file}")
            sys.exit(1)

        print("\n" + "=" * 80)
        print(f"RUNNING SINGLE BENCHMARK: {args.benchmark.replace('_', ' ').title()}")
        print("=" * 80)

        result = runner.run_benchmark(benchmark_file)
        runner.results.append(result)

        if result.success:
            print(f"\n[✓] Benchmark passed in {result.duration:.2f}s")
        else:
            print(f"\n[✗] Benchmark failed in {result.duration:.2f}s")
            if result.error:
                print(f"Error: {result.error}")

        sys.exit(0 if result.success else 1)
    else:
        # Run all benchmarks
        runner.run_all()
        runner.print_summary()
        sys.exit(runner.get_exit_code())


if __name__ == "__main__":
    main()
