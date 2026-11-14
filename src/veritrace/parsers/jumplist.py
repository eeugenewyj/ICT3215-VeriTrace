from .windows import WindowsCsvAdapter


class JumpListAdapter(WindowsCsvAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__("jumplist", *args, **kwargs)
