def do_nothing(*args,**kwargs):
    pass

class Dummy(object):
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, item):
        return do_nothing


class DummyDefault(Dummy):
    pass


class DummyResourceRequest(Dummy):
    pass


class DummyResourceVariant(Dummy):
    pass


class DummyDisplayList(Dummy):
    pass