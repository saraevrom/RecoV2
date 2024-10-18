import io

# Stripping block of imports.
# STRIP IMPORT
import this
from datetime import datetime

# Test data

# Strip and replace.
# STRIP
a = "Strip This"
# REPLACE
# print("Stripped!")
# END

# Strip and replace. Since this block is broken it won't work.
# STRIP
a1 = "Strip 1"
# REPLACE
# print("Stripped!")
a1 = "OOPS"
# END

# Bracelike strip.
# STRIP
x = "Strip 2"
# END


# One line stripping
# STRIP
y = "Strip 3"

# Another line stripping.
# STRIP
z = "Strip 4"

# Stripping entire class.
# STRIP CLASS
class RemoveClass(object):
    def __init__(self, azaza):
        self.azaza = azaza

# Stripping won't touch this line
x42 = 0
