"""
Result type for standardized error handling.

This module provides a Result[T, E] pattern for functions that can either succeed
with a value or fail with an error. This eliminates the need for mixed return
patterns (None vs empty collections) and provides consistent error handling.

Examples:
    Basic usage:

    ```python
    def divide(a: float, b: float) -> Result[float, str]:
        if b == 0:
            return Error("Division by zero")
        return Success(a / b)

    # Usage
    result = divide(10, 2)
    if result.is_success():
        print(f"Result: {result.value}")
    else:
        print(f"Error: {result.error}")
    ```

    With custom error types:

    ```python
    from studiorum.core.exceptions import ValidationError

    def validate_content(data: dict) -> Result[Content, ValidationError]:
        try:
            content = Content.model_validate(data)
            return Success(content)
        except ValidationError as e:
            return Error(e)
    ```
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")  # Success value type
E = TypeVar("E")  # Error type
U = TypeVar("U")  # Mapped success type


class Result[T, E](ABC):
    """
    Abstract base class for Result types.

    A Result represents the outcome of an operation that can either succeed
    with a value of type T or fail with an error of type E.
    """

    @abstractmethod
    def is_success(self) -> bool:
        """Return True if this is a Success result."""
        ...

    @abstractmethod
    def is_error(self) -> bool:
        """Return True if this is an Error result."""
        ...

    @abstractmethod
    def unwrap(self) -> T:
        """
        Return the success value.

        Raises:
            RuntimeError: If this is an Error result.
        """
        ...

    @abstractmethod
    def unwrap_or(self, default: T) -> T:
        """Return the success value or a default if this is an Error."""
        ...

    @abstractmethod
    def unwrap_or_else(self, default_fn: Callable[[E], T]) -> T:
        """Return the success value or the result of calling default_fn with the error."""
        ...

    @abstractmethod
    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        """Transform the success value using the given function."""
        ...

    @abstractmethod
    def map_error(self, fn: Callable[[E], Any]) -> Result[T, Any]:
        """Transform the error value using the given function."""
        ...

    @abstractmethod
    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain another Result-returning operation on success."""
        ...


@dataclass(frozen=True)
class Success[T, E](Result[T, E]):
    """
    Represents a successful result containing a value.

    Args:
        value: The successful result value.
    """

    value: T

    def is_success(self) -> bool:
        """Return True since this is a Success result."""
        return True

    def is_error(self) -> bool:
        """Return False since this is a Success result."""
        return False

    def unwrap(self) -> T:
        """Return the success value."""
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Return the success value (ignoring the default)."""
        return self.value

    def unwrap_or_else(self, default_fn: Callable[[E], T]) -> T:
        """Return the success value (ignoring the default function)."""
        return self.value

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        """Transform the success value using the given function."""
        return Success(fn(self.value))

    def map_error(self, fn: Callable[[E], Any]) -> Result[T, Any]:
        """Return self since there's no error to transform."""
        return self  # type: ignore[return-value]

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain another Result-returning operation."""
        return fn(self.value)


@dataclass(frozen=True)
class Error[T, E](Result[T, E]):
    """
    Represents a failed result containing an error.

    Args:
        error: The error that caused the failure.
    """

    error: E

    def is_success(self) -> bool:
        """Return False since this is an Error result."""
        return False

    def is_error(self) -> bool:
        """Return True since this is an Error result."""
        return True

    def unwrap(self) -> T:
        """
        Raise an error since this is an Error result.

        Raises:
            RuntimeError: Always, containing the error information.
        """
        raise RuntimeError(f"Called unwrap() on Error result: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Return the default value since this is an Error result."""
        return default

    def unwrap_or_else(self, default_fn: Callable[[E], T]) -> T:
        """Return the result of calling default_fn with the error."""
        return default_fn(self.error)

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        """Return self since there's no success value to transform."""
        return self  # type: ignore[return-value]

    def map_error(self, fn: Callable[[E], Any]) -> Result[T, Any]:
        """Transform the error value using the given function."""
        return Error(fn(self.error))

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Return self since there's no success value to chain with."""
        return self  # type: ignore[return-value]


# Type alias for convenience
ResultType = Success[T, E] | Error[T, E]


def collect_results[T, E](results: list[Result[T, E]]) -> Result[list[T], list[E]]:
    """
    Collect multiple Results into a single Result.

    If all Results are successful, returns Success with a list of all values.
    If any Results are errors, returns Error with a list of all errors.

    Args:
        results: List of Result objects to collect.

    Returns:
        Success with list of values if all succeeded, Error with list of errors otherwise.

    Examples:
        >>> results = [Success(1), Success(2), Success(3)]
        >>> collected = collect_results(results)
        >>> # Returns Success([1, 2, 3])
        >>>
        >>> results = [Success(1), Error("fail"), Success(3)]
        >>> collected = collect_results(results)
        >>> # Returns Error(["fail"])
    """
    successes: list[T] = []
    errors: list[E] = []

    for result in results:
        if result.is_success():
            successes.append(result.unwrap())
        else:
            # We know this is an Error, so we can access the error attribute
            errors.append(result.error)  # type: ignore[attr-defined]

    if errors:
        return Error(errors)
    return Success(successes)


def try_result[T](fn: Callable[[], T]) -> Result[T, Exception]:
    """
    Execute a function and wrap the result/exception in a Result.

    Args:
        fn: Function to execute.

    Returns:
        Success with the function result, or Error with the exception.

    Examples:
        >>> result = try_result(lambda: 10 / 0)
        >>> # Returns Error(ZeroDivisionError("division by zero"))
        >>>
        >>> result = try_result(lambda: 10 / 2)
        >>> # Returns Success(5.0)
    """
    try:
        return Success(fn())
    except Exception as e:
        return Error(e)


def async_try_result[T](fn: Callable[[], T]) -> Result[T, Exception]:
    """
    Async version of try_result.

    Args:
        fn: Async function to execute.

    Returns:
        Success with the function result, or Error with the exception.
    """
    # Note: This is a placeholder for async implementation
    # In a full implementation, this would handle async functions
    return try_result(fn)
