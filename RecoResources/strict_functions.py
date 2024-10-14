
class Default(object):
    @classmethod
    def default(cls):
        raise NotImplementedError

    @classmethod
    def to_strict_function(cls):
        return StrictReturnFunction(cls,cls.default)

class StrictReturnFunction(object):
    def __init__(self,return_type,function):
        self.return_type = return_type
        self.function = function

    def __call__(self, *args, **kwargs):
        result = self.function(*args,**kwargs)
        if not isinstance(result,self.return_type):
            raise TypeError("Function returned wrong type")
        return result


class StrictFunction(object):
    def __init__(self, return_type):
        self.return_type = return_type

    def __call__(self, function):
        return StrictReturnFunction(self.return_type,function)
