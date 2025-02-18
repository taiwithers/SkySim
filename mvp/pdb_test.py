from ipdb import set_trace as breakpoint  # overriding builtin breakpoint()

print("Initial print statement")

for i in range(10):
    print(f"{i=}")
    if i == 5:
        breakpoint()


raise Exception()
