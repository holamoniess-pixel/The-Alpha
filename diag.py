import sys
import os
print(f"Executable: {sys.executable}")
print("Path:")
for p in sys.path:
    print(p)
try:
    import numpy
    print(f"Numpy: {numpy.__file__}")
except ImportError as e:
    print(f"Numpy Import Error: {e}")
