"""Pytest configuration and global environment fixture setup."""

import os
import sys

# Ensure offline operation for HuggingFace and Sentence-Transformers
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"

