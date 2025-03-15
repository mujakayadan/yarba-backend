"""LLM tester implementation."""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from config import get_logger

from .base import BaseLLM
from .runner import LLMRunner

logger = get_logger(__name__)


@dataclass
class TestCase:
    """Test case for LLM evaluation.

    This class represents a single test case for evaluating
    LLM performance and accuracy.
    """

    prompt: str
    expected_output: Optional[str] = None
    context: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class TestResult(BaseModel):
    """Result of an LLM test case.

    This class holds the results of running a test case,
    including the response, timing, and validation results.
    """

    prompt: str
    response: Optional[str]
    expected_output: Optional[str]
    is_valid: bool
    duration_ms: float
    metadata: Dict[str, Any]


class LLMTester:
    """Tester class for evaluating LLM performance.

    This class provides functionality for running test cases
    against LLM implementations and analyzing their performance.
    """

    def __init__(self, runner: LLMRunner):
        """Initialize the LLM tester.

        Args:
            runner: LLM runner instance to test
        """
        self.runner = runner
        self.results: List[TestResult] = []

    async def run_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case.

        Args:
            test_case: Test case to run

        Returns:
            TestResult: Results of the test case
        """
        start_time = asyncio.get_event_loop().time()

        # Generate response
        if test_case.context:
            response = await self.runner.generate_with_context(
                test_case.prompt, test_case.context
            )
        else:
            response = await self.runner.generate(test_case.prompt)

        duration = (asyncio.get_event_loop().time() - start_time) * 1000

        # Validate response
        is_valid = False
        if response:
            is_valid = await self.runner.llm.validate_response(response)
            if test_case.expected_output:
                is_valid = is_valid and self._compare_outputs(
                    response, test_case.expected_output
                )

        # Create result
        result = TestResult(
            prompt=test_case.prompt,
            response=response,
            expected_output=test_case.expected_output,
            is_valid=is_valid,
            duration_ms=duration,
            metadata=test_case.metadata or {},
        )

        self.results.append(result)
        return result

    async def run_tests(self, test_cases: List[TestCase]) -> List[TestResult]:
        """Run multiple test cases.

        Args:
            test_cases: List of test cases to run

        Returns:
            List[TestResult]: Results of all test cases
        """
        results = []
        for test_case in test_cases:
            result = await self.run_test(test_case)
            results.append(result)
        return results

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of test results.

        Returns:
            Dict[str, Any]: Summary statistics of test results
        """
        if not self.results:
            return {}

        total_tests = len(self.results)
        valid_responses = sum(1 for r in self.results if r.is_valid)
        avg_duration = sum(r.duration_ms for r in self.results) / total_tests

        return {
            "total_tests": total_tests,
            "successful_tests": valid_responses,
            "success_rate": valid_responses / total_tests,
            "average_duration_ms": avg_duration,
            "total_duration_ms": sum(r.duration_ms for r in self.results),
        }

    def clear_results(self) -> None:
        """Clear all test results."""
        self.results.clear()

    def _compare_outputs(self, actual: str, expected: str) -> bool:
        """Compare actual and expected outputs.

        Args:
            actual: Actual output from LLM
            expected: Expected output

        Returns:
            bool: True if outputs match according to comparison rules
        """
        # Basic string comparison for now
        # Could be extended with more sophisticated comparison methods
        return actual.strip() == expected.strip()
