
# STRIP
from .strict_functions import Default
from .resource_input import ResourceInput, ResourceInputWidget, ResourceForm, ResourceRequest
from .resource_output import ResourceOutput, ResourceDisplay, DisplayList
# REPLACE
# from .dummy import DummyDefault as Default
# from .dummy import DummyResourceRequest as ResourceRequest
# from .dummy import DummyDisplayList as DisplayList
# END


# STRIP
# REPLACE
# from .dummy import DummyResourceRequest as ResourceVariant
# END

# Core resources
from .RecoResourcesCore import *

# Base resources
from .RecoResourcesBase import *


# Auxiliary resources
from .RecoResourcesNonbase import *

#Shipped resources
from .RecoResourcesShipped import *


from .strict_functions import StrictFunction

# Resources have 5 types
# 1) CORE: PartiallyLoadedResource, BundleResource - what you need to load anything else
# 2) BASE: Building blocks for complex resources (Valued resources, Combine, Alternate, Array, Option, File)
# 3) NONBASE: Resources not representable via base
# 4) SHIPPED: stock resources inherited from BASE category
# 5) USER: user provided resources


