"""
Konfiguracja pytest - dodaje sciezke do modulu app.
"""
import sys
from pathlib import Path

# Dodanie katalogu backend do sciezki importow
sys.path.insert(0, str(Path(__file__).parent.parent))
