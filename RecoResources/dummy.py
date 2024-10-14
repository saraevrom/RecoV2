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


class DummyDisplayList(object):
    def __init__(self,is_white:bool,display_list:list):
        self.is_white = is_white
        self.display_list = display_list

    def is_allowed(self,item):
        return (item in self.display_list) == self.is_white

    @staticmethod
    def whitelist(display_list):
        return DummyDisplayList(True,display_list)

    @staticmethod
    def blacklist(display_list):
        return DummyDisplayList(False,display_list)

    @staticmethod
    def default():
        return DisplayList.blacklist([])
