import inspect
import sys

from unstructured.ingest.interfaces import BaseIngestDoc
from unstructured.ingest import connector

import importlib
import os

# Calculate the path to the "connector" directory
connector_dir = os.path.join(os.path.dirname(__file__), "connector")
print(f"connector_dir: {connector_dir}")

# Import all modules using the * wildcard
module_names = [
    name[:-3] for name in os.listdir(connector_dir)
    if name.endswith('.py') and not name.startswith('__init__')
]

print(f"module_names: {module_names}")


# print(module_names)

class ClassRegistry:
    _registry = {}

    @classmethod
    def register(cls, connector_name, class_type):
        cls._registry[connector_name] = class_type

    @classmethod
    def get_class(cls, connector_name):
        return cls._registry.get(connector_name, None)

# Dynamically populate the class registry
for name, cls in inspect.getmembers(sys.modules[__name__], inspect.isclass):
    if issubclass(cls, BaseIngestDoc) and cls != BaseIngestDoc:
        ClassRegistry.register(cls.connector_name, cls)
    print(ClassRegistry._registry)

def create_instance_from_dict(data_dict):
    connector_name = data_dict.pop('connector_name')
    subclass = ClassRegistry.get_class(connector_name)
    if subclass:
        return subclass.from_dict(data_dict)
    else:
        raise ValueError(f"Unknown class: {connector_name}")
    
def init_registry():
    for module_name in module_names:
        # importlib.import_module(f'unstructured.ingest.connector.{module_name}')
        module = importlib.import_module(f'unstructured.ingest.connector.{module_name}')
        # Iterate through the attributes of the module to find subclasses

        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and not inspect.isabstract(obj) and obj != BaseIngestDoc:
                ancestor_names = [ancestor.__name__ for ancestor in obj.mro()]
                if "BaseIngestDoc" in ancestor_names:
                    print(f"Registering {obj.__name__}")
                    try:
                        ClassRegistry.register(obj.connector_name, obj)
                    except AttributeError as e:
                        print(f"Error registering {obj.__name__}: {e}")
