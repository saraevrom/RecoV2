from typing import List, Any


def estimate_shape(data:List[List[Any]]):
    if len(data)==0:
        return 0,0
    else:
        rows = len(data)
        columns = len(data[0])
        for row in data:
            if len(row)!=columns:
                return None
        return rows,columns


def format_str(x):
    if isinstance(x,float) or isinstance(x,int):
        return f"{x:>5}"
    else:
        return f"{x}"

class Matrix(object):
    '''
    Explicit matrix class for meta-magic
    '''
    def __init__(self,matrix_data:List[List[Any]]):
        shape = estimate_shape(matrix_data)
        if shape is None:
            raise ValueError(f"Array {matrix_data} has no consistent rows")
        self.matrix_data = matrix_data
        self.shape = shape


    def __repr__(self):
        s = "[\n"
        for i in range(self.rows):
            v = ", ".join(map(format_str,self.matrix_data[i]))
            s += f" [{v}],\n"
        s+="]"
        return s


    @classmethod
    def blank(cls,rows,columns, fill_value=None):
        matdata = []
        for i in range(rows):
            matdata.append([fill_value]*columns)
        return cls(matdata)

    def __getitem__(self, item):
        return self.matrix_data[item[0]][item[1]]

    def __setitem__(self, key, value):
        self.matrix_data[key[0]][key[1]] = value

    def is_square(self):
        return self.shape[0]==self.shape[1]

    @property
    def rows(self):
        return self.shape[0]

    @property
    def columns(self):
        return self.shape[1]

    def __matmul__(self, other):
        if self.columns != other.rows:
            raise ValueError(f"Cannot multiply matrix with shape {self.shape} by {other.shape}")
        res = type(self).blank(self.rows,other.columns)
        for i in range(self.rows):
            for j in range(other.columns):
                s = None
                for k in range(self.columns):
                    a = self[i,k] * other[k,j]
                    if s is None:
                        s = a
                    else:
                        s += a
                res[i, j] = s
        return res

    @classmethod
    def diagonal(cls, diagonal, other_value = 0.0):
        res = cls.blank(len(diagonal),len(diagonal),other_value)
        cast = type(other_value)
        for i in range(len(diagonal)):
            res[i,i] = cast(diagonal[i])
        return res

    @classmethod
    def identity(cls, size, diag_value=1.0, other_value=0.0):
        diag = [diag_value]*size
        return cls.diagonal(diag,other_value)

    def swap_rows(self,row1,row2):
        self.matrix_data[row1], self.matrix_data[row2] = self.matrix_data[row2], self.matrix_data[row1]

    def row(self,i):
        return self.matrix_data[i]

    def column(self,j):
        col = []
        for i in range(self.rows):
            col.append(self.matrix_data[i][j])
        return col

    def squeeze(self):
        state = int(self.rows == 1)*2+int(self.columns == 1)
        if state == 0:          # Rect matrix
            return self
        elif state == 1:        # Matrix is column
            return self.column(0)
        elif state == 2:        # Matrix is row
            return self.row(0)
        else:                   # Matrix is single value
            return self.matrix_data[0][0]

    def to_vec4(self):
        from .vectors import Vector4
        if self.shape==(4,1):
            return Vector4(*self.column(0))
        else:
            raise ValueError(f"Matrix of shape {self.shape} cannot be turned into (column) 4d vector")
