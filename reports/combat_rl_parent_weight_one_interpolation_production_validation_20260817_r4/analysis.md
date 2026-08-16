# Promoted alpha-0.20 production validation r4

The post-Headbutt-fix production command completed five games without runtime failures. Floors were `28, 31, 16, 27, 36`, for a mean of `27.6`. Four games defeated the Act 1 boss, and one defeated the Act 2 boss and entered Act 3. No victory was achieved.

The simulator trace remained empty for the entire batch. In particular, none of the six paired Headbutt selection-boundary rows from r3 recurred. This supplies fresh live evidence for the focused Flight, Curl Up, and Double Tap timing fix without adding another test pass.

The decision trace remained bounded at `7,540,231` bytes and the simulator trace at zero bytes. The promoted checkpoint remains the production baseline. With the current mechanics trace clean, the next work should use run and decision evidence to address policy quality rather than continue mechanics cleanup without a new signal.
