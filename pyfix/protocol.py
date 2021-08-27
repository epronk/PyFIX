import importlib

def LoadProtocol(version):
    return importlib.import_module(version)
