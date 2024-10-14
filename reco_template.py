from reco_resources_bundle import RecoResourcesBundle

model = RecoResourcesBundle.open("model.json")
model.execute()

# Setting resource
# model.set("a",4)
# model.set("b",5)

# set_resource and get_resource will also work
# Small reminder that HDF resource and numpy array resource have set_value


# Run model
model.run_model()

# Getting results (use get() or get_resource())
# result = model.get("result")

# Run action. Use method name that was marked as action
# model.run_action("print_hello")
