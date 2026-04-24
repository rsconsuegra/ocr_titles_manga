"""Base class for image preprocessing steps."""

from abc import ABC, abstractmethod

import numpy as np


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

    @abstractmethod
    def process(self, image: np.ndarray, config: dict) -> tuple[np.ndarray, dict]:
        """Apply the preprocessing step.

        Args:
            image: Input image as a numpy array (BGR or grayscale).
            config: Step-specific configuration from the YAML file.

        Returns:
            Tuple of (processed_image, metadata_dict).

        """
