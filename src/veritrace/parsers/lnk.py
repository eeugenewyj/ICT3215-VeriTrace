from .windows import WindowsCsvAdapter


class LnkAdapter(WindowsCsvAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__("lnk", *args, **kwargs)
