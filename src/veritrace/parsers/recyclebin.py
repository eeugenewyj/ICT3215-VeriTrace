from .windows import WindowsCsvAdapter


class RecycleBinAdapter(WindowsCsvAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__("recyclebin", *args, **kwargs)
