from .windows import WindowsCsvAdapter


class PrefetchAdapter(WindowsCsvAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__("prefetch", *args, **kwargs)
