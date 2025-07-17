import os
import importlib
import inspect
from .base_parser import BaseParser

# Dynamically import all parser modules in this directory
# and collect the parser classes.

# List of all parser classes found
ALL_PARSERS = []

# Get the directory of the current module
current_dir = os.path.dirname(__file__)

# Iterate over all files in the directory
for filename in os.listdir(current_dir):
    # Check if it's a Python file and not this __init__.py or base_parser.py
    if filename.endswith('.py') and not filename.startswith('__') and filename != 'base_parser.py':
        # Import the module
        module_name = f"parsers.{filename[:-3]}"
        module = importlib.import_module(module_name)

        # Find all classes in the module that are subclasses of BaseParser
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseParser) and obj is not BaseParser:
                ALL_PARSERS.append(obj)

print(f"Loaded {len(ALL_PARSERS)} parsers: {[p.get_name() for p in ALL_PARSERS]}")
