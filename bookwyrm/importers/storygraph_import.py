""" handle reading a csv from storygraph"""
from . import Importer


class StorygraphImporter(Importer):
    """csv downloads from librarything"""

    service = "Storygraph"
