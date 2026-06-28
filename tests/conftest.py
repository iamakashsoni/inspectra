# Copyright (c) 2025-2026 Akash Soni
#
# Licensed under the MIT License. See LICENSE in the project root
# for the full license text. You may not claim authorship of this work.

"""Test fixtures."""
import sys
from pathlib import Path

# Make src/ inspectable without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
