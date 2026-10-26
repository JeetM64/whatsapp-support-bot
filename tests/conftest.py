"""Keep the test suite offline even when a local model cache is available."""

import os

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
