from .base import JsonFileStore


class AnalysisConfigStore(JsonFileStore):
    def __init__(self, **kwargs):
        super().__init__("analysis_params.json", **kwargs)
