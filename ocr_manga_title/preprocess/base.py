"""Base class for image preprocessing steps."""

import logging
import threading
from abc import ABC, abstractmethod
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_STEP_TIMEOUT = 120


class BasePreProcessor(ABC):
    """Abstract interface for a single preprocessing step.

    Each step receives a numpy image and a config dict, and returns
    the processed image along with metadata.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Machine-readable identifier for this step."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether the step's runtime dependencies are installed."""

    @property
    def timeout(self) -> int:
        """Maximum seconds this step is allowed to run before timing out."""
        return DEFAULT_STEP_TIMEOUT

    @abstractmethod
    def process(self, image: np.ndarray, config: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        """Apply the preprocessing step.

        Args:
            image: Input image as a numpy array (BGR or grayscale).
            config: Step-specific configuration from the YAML file.

        Returns:
            Tuple of (processed_image, metadata_dict).

        """


def run_step_with_timeout(
    step: BasePreProcessor,
    image: np.ndarray,
    config: dict[str, Any],
    timeout_override: int | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Execute a step's process() with a timeout guard.

    Runs the step in a daemon thread.  If the step does not finish within
    *timeout* seconds a :class:`TimeoutError` is raised.  The underlying
    thread may continue running (it is a daemon and will not block process
    exit), but the caller receives the error immediately.

    Args:
        step: The preprocessing step to execute.
        image: Input image array.
        config: Step-specific configuration.
        timeout_override: Override the step's default timeout (seconds).

    Returns:
        Tuple of (processed_image, metadata_dict).

    Raises:
        TimeoutError: If the step exceeds its time limit.

    """
    timeout_seconds = timeout_override or step.timeout

    result: list[tuple[np.ndarray, dict[str, Any]] | None] = [None]
    exception: list[Exception | None] = [None]

    def _target() -> None:
        try:
            result[0] = step.process(image, config)
        except Exception as exc:
            exception[0] = exc

    thread = threading.Thread(target=_target, daemon=True, name=f"pp-{step.name}")
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        logger.error(
            "Step '%s' timed out after %ds — returning error to caller",
            step.name,
            timeout_seconds,
        )
        raise TimeoutError(
            f"Preprocessing step '{step.name}' timed out after {timeout_seconds}s"
        )

    if exception[0] is not None:
        raise exception[0]

    return result[0]  # type: ignore[return-value]
