# Repaired combat RL training batch r1

## Result

The repaired transition path completed 10 live training games from the frozen
entry checkpoint. It accepted 2,187 transitions and performed 515 Adam updates
without replay rejection, pending-transition finalization failure, executed
action binding failure, RL agent failure, or strict NaN evidence.

The 10 training floors were `25, 33, 16, 33, 22, 33, 22, 33, 33, 31` (mean
28.1, median 32). Nine runs entered Act 2 and five reached an Act 2 boss. There
were no victories. These outcomes are descriptive only because the batch used
training exploration and expert mixing.

## Transition integrity

The runtime log contained at least 155 outer guard replacements: 21 lethal, 89
energy, 21 potion, 18 survival, and 6 boss replacements. These are the paths on
which the pre-repair implementation could train against the proposed action
instead of the action sent to CommunicationMod. The repaired binding path
reported zero failures throughout the batch.

## Checkpoint

The output checkpoint is `rl_combat_model_ep19_steps14035.pth`, SHA-256
`dcbe7fddc212aaa6ae2a09adebe44265f83d4fd8c92a80e3269a22f7e5843e3a`.
All model tensors are finite. Relative to the entry model, whole-model L2 drift
is 2.48%; hidden, value, and advantage stream drift is 11.71%, 13.01%, and
19.34%, respectively. The unused legacy output layer is unchanged.

The filename says episode 19 while the payload says episode 10. This is an
existing bookkeeping defect, so the artifact must be identified by path, hash,
and `total_steps=14035`, not episode alone.

## Decision

Do not extend training yet. Run the repaired candidate and the frozen entry
checkpoint on one fresh, preregistered, ordered seed pool with `epsilon=0`.
Continue repaired training only if paired outcome evidence improves without
integrity warnings; otherwise inspect learner stability and replay/target
persistence before consuming more games.
