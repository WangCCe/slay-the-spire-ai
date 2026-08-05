# State-Conditioned Card-Reward Collapse Audit

## Result

- Status: `mechanism_narrowed_causality_unresolved`
- Terminal verdict: `experiment_stopped_at_canary`
- Canary blocker: `card_reward_selected_kind_saturation`
- Training chunks: `64`
- Holdout accessed: `false`

## Exact Boundaries

| Predicate | First observed chunk | Earliest persistent chunk |
| --- | ---: | ---: |
| `selected_take_only` | not observed | not observed |
| `greedy_take_only` | 2 | 2 |

## Action-Family Evidence

- Training card-reward decisions: `31571`
- Mean take candidate share: `0.749936646862`
- Mean take probability mass: `0.808513819582`
- Mean take probability excess over candidate share: `0.0585771727198`
- Mean candidate entropy minus kind entropy: `0.881483857013`
- Initial canary selected kinds: `{"skip": {"count": 59, "rate": 0.06101344364012409}, "take": {"count": 908, "rate": 0.9389865563598759}}`
- Trained canary selected kinds: `{"take": {"count": 1458, "rate": 1.0}}`
- Initial canary greedy take-only: `false`
- Trained canary greedy take-only: `true`

## Training Outcomes And Controls

- Outcomes: `{"effective_floor": {"count": 4096, "max": 50.0, "mean": 14.1416015625, "median": 16.0, "min": 2.0}, "episode_count": 4096, "outcomes": {"player_loss": 4055}, "total_reward": {"count": 4096, "max": 0.8771929824561415, "mean": 0.2480982730263158, "median": 0.2807017543859649, "min": 0.03508771929824561}, "unsupported_episodes": 41, "unsupported_reasons": {"unsupported_shop_courier_restock_semantics": 41}, "victories": 0}`
- `event` decisions: `9097`; selected kinds: `{"event_option": {"count": 9097, "rate": 1.0}}`
- `route` decisions: `57256`; selected kinds: `{"map_node": {"count": 57256, "rate": 1.0}}`
- `shop` decisions: `9180`; selected kinds: `{"buy_card": {"count": 3914, "rate": 0.4263616557734205}, "buy_potion": {"count": 945, "rate": 0.10294117647058823}, "buy_relic": {"count": 374, "rate": 0.040740740740740744}, "leave": {"count": 3451, "rate": 0.37592592592592594}, "remove_card": {"count": 496, "rate": 0.05403050108932462}}`

## Chunk Trajectory

| Chunk | Pass | Eligible cards | Selected take rate | Greedy take rate | Mean take probability | Min take-skip margin | Mean floor | Unsupported | Post-update model delta L2 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 477 | 0.765560165975 | 0.935684647303 | 0.751517369295 | -0.00831973552704 | 13.828125 | 0 | not observed |
| 1 | 0 | 458 | 0.76688453159 | 0.997821350763 | 0.753530294095 | -0.0027469098568 | 13.703125 | 1 | 0.228058485721 |
| 2 | 0 | 438 | 0.764840182648 | 1 | 0.755267673565 | 0.00703430175781 | 12.203125 | 0 | 0.188179713041 |
| 3 | 0 | 483 | 0.741200828157 | 1 | 0.757185120872 | 0.0131346285343 | 13.46875 | 0 | 0.164843081069 |
| 4 | 0 | 479 | 0.740124740125 | 1 | 0.758138553262 | 0.0147129297256 | 13.78125 | 0 | 0.146211821397 |
| 5 | 0 | 450 | 0.748888888889 | 1 | 0.756727679135 | 0.0216160416603 | 12.78125 | 0 | 0.132625085228 |
| 6 | 0 | 457 | 0.741865509761 | 1 | 0.760375445515 | 0.0218444764614 | 13.53125 | 2 | 0.121637297464 |
| 7 | 0 | 459 | 0.75374732334 | 1 | 0.760135783848 | 0.0216853618622 | 12.84375 | 3 | 0.112356682311 |
| 8 | 0 | 457 | 0.752711496746 | 1 | 0.761886762017 | 0.0279113948345 | 13.9375 | 0 | 0.105657279728 |
| 9 | 0 | 483 | 0.756701030928 | 1 | 0.761761042957 | 0.0268276929855 | 13.75 | 0 | 0.0989943617168 |
| 10 | 0 | 496 | 0.753479125249 | 1 | 0.763875461962 | 0.0345529913902 | 14.296875 | 0 | 0.0936111975176 |
| 11 | 0 | 481 | 0.767489711934 | 1 | 0.764368672828 | 0.0418986082077 | 13.8125 | 4 | 0.0893915520092 |
| 12 | 0 | 486 | 0.815573770492 | 1 | 0.765984931009 | 0.0571404993534 | 13.90625 | 0 | 0.0854434629721 |
| 13 | 0 | 485 | 0.781893004115 | 1 | 0.76738845243 | 0.0530658960342 | 14.03125 | 1 | 0.0836901401168 |
| 14 | 0 | 493 | 0.75702811245 | 1 | 0.766052600729 | 0.0310595333576 | 14.109375 | 0 | 0.0809096056391 |
| 15 | 0 | 461 | 0.756465517241 | 1 | 0.769906454908 | 0.0586235523224 | 12.703125 | 0 | 0.0792583596332 |
| 16 | 1 | 514 | 0.77626459144 | 1 | 0.771770007278 | 0.0619445443153 | 14.40625 | 1 | 0.078944961628 |
| 17 | 1 | 444 | 0.797777777778 | 1 | 0.774279087527 | 0.0656621456146 | 13.171875 | 0 | 0.0767290235026 |
| 18 | 1 | 403 | 0.77886977887 | 1 | 0.774246962123 | 0.063296020031 | 11.9375 | 0 | 0.0747759643868 |
| 19 | 1 | 495 | 0.774900398406 | 1 | 0.776965426236 | 0.088791847229 | 13.28125 | 1 | 0.0739554158109 |
| 20 | 1 | 507 | 0.816568047337 | 1 | 0.779018918297 | 0.0921111106873 | 14.21875 | 0 | 0.073470204757 |
| 21 | 1 | 473 | 0.761099365751 | 1 | 0.77803426133 | 0.0940296947956 | 13.828125 | 0 | 0.0719883716138 |
| 22 | 1 | 477 | 0.779874213836 | 1 | 0.780775023952 | 0.102619409561 | 13.734375 | 0 | 0.0709848979023 |
| 23 | 1 | 457 | 0.800865800866 | 1 | 0.785604290833 | 0.10657954216 | 13.03125 | 1 | 0.0692771689567 |
| 24 | 1 | 467 | 0.811040339703 | 1 | 0.787822796532 | 0.124337762594 | 13.359375 | 0 | 0.0699338189817 |
| 25 | 1 | 452 | 0.787610619469 | 1 | 0.789908949013 | 0.140538990498 | 13 | 0 | 0.069553589284 |
| 26 | 1 | 524 | 0.80303030303 | 1 | 0.793051097089 | 0.152165234089 | 14.9375 | 0 | 0.0689682645413 |
| 27 | 1 | 497 | 0.792156862745 | 1 | 0.794247963071 | 0.167047739029 | 14.3125 | 0 | 0.0692480853263 |
| 28 | 1 | 512 | 0.798058252427 | 1 | 0.796121095831 | 0.148679047823 | 14.78125 | 0 | 0.0683385514686 |
| 29 | 1 | 476 | 0.834381551363 | 1 | 0.799770922522 | 0.16067814827 | 14.171875 | 0 | 0.0693687263987 |
| 30 | 1 | 505 | 0.815841584158 | 1 | 0.80150916075 | 0.182075560093 | 14.40625 | 0 | 0.0689970848854 |
| 31 | 1 | 482 | 0.783950617284 | 1 | 0.804015545947 | 0.185886621475 | 13.109375 | 0 | 0.0680638051931 |
| 32 | 2 | 512 | 0.798828125 | 1 | 0.80535266756 | 0.168795049191 | 14.125 | 2 | 0.0695757515963 |
| 33 | 2 | 458 | 0.804255319149 | 1 | 0.808862659071 | 0.209996074438 | 13.703125 | 1 | 0.0690932918128 |
| 34 | 2 | 484 | 0.839835728953 | 1 | 0.80743165345 | 0.149957865477 | 13.671875 | 1 | 0.070308756889 |
| 35 | 2 | 474 | 0.806315789474 | 1 | 0.812284961586 | 0.219266653061 | 13.734375 | 2 | 0.0708465154111 |
| 36 | 2 | 454 | 0.823529411765 | 1 | 0.81645891599 | 0.24277856946 | 13.484375 | 0 | 0.0710286169999 |
| 37 | 2 | 462 | 0.8125 | 1 | 0.819043429643 | 0.262372136116 | 13.65625 | 1 | 0.0708449135595 |
| 38 | 2 | 490 | 0.845238095238 | 1 | 0.822666703535 | 0.261975824833 | 14.65625 | 1 | 0.0688407608955 |
| 39 | 2 | 470 | 0.810126582278 | 1 | 0.824155031609 | 0.276015251875 | 13.484375 | 1 | 0.0707980294951 |
| 40 | 2 | 485 | 0.828973843058 | 1 | 0.826406534706 | 0.286814510822 | 14.34375 | 0 | 0.0706499166032 |
| 41 | 2 | 491 | 0.816 | 1 | 0.828582990877 | 0.275046527386 | 14.453125 | 0 | 0.0699059971227 |
| 42 | 2 | 498 | 0.837623762376 | 1 | 0.829914333361 | 0.298901945353 | 14.796875 | 0 | 0.071565580863 |
| 43 | 2 | 445 | 0.821029082774 | 1 | 0.830341832605 | 0.292939007282 | 12.875 | 0 | 0.0704904157147 |
| 44 | 2 | 498 | 0.825301204819 | 1 | 0.833064596321 | 0.234026551247 | 14.0625 | 2 | 0.0687013285706 |
| 45 | 2 | 453 | 0.830396475771 | 1 | 0.838480171803 | 0.290572136641 | 13.46875 | 1 | 0.0697839795663 |
| 46 | 2 | 563 | 0.829225352113 | 1 | 0.838350696198 | 0.315163910389 | 16.484375 | 0 | 0.0694509421655 |
| 47 | 2 | 538 | 0.848708487085 | 1 | 0.838090557254 | 0.33430069685 | 15.359375 | 0 | 0.0706684295093 |
| 48 | 3 | 539 | 0.838181818182 | 1 | 0.841021140515 | 0.255820631981 | 15.15625 | 0 | 0.0708505787666 |
| 49 | 3 | 494 | 0.819639278557 | 1 | 0.843170677782 | 0.308266043663 | 14.515625 | 2 | 0.0703127663658 |
| 50 | 3 | 496 | 0.862903225806 | 1 | 0.843469743229 | 0.328821241856 | 14.375 | 0 | 0.0694793964167 |
| 51 | 3 | 537 | 0.843866171004 | 1 | 0.845394617149 | 0.314241945744 | 15.328125 | 1 | 0.0696639532599 |
| 52 | 3 | 519 | 0.831119544592 | 1 | 0.847796909502 | 0.384079992771 | 14.796875 | 0 | 0.0715787354528 |
| 53 | 3 | 499 | 0.832 | 1 | 0.849212310574 | 0.360611498356 | 14.609375 | 2 | 0.0720299949257 |
| 54 | 3 | 520 | 0.825 | 1 | 0.853397187405 | 0.322213888168 | 14.75 | 3 | 0.0702936613073 |
| 55 | 3 | 498 | 0.882583170254 | 1 | 0.85678446517 | 0.402421951294 | 14.609375 | 2 | 0.0674912471821 |
| 56 | 3 | 500 | 0.838323353293 | 1 | 0.856806777212 | 0.371475815773 | 14.46875 | 1 | 0.0714930096736 |
| 57 | 3 | 522 | 0.877394636015 | 1 | 0.859426858589 | 0.348973155022 | 15.078125 | 0 | 0.0709366932788 |
| 58 | 3 | 542 | 0.832116788321 | 1 | 0.863647990583 | 0.422379314899 | 15.625 | 0 | 0.0721357128278 |
| 59 | 3 | 497 | 0.873046875 | 1 | 0.863720236154 | 0.385562390089 | 14.625 | 0 | 0.0714909158667 |
| 60 | 3 | 524 | 0.861682242991 | 1 | 0.868627577526 | 0.487312495708 | 15.796875 | 1 | 0.072967880704 |
| 61 | 3 | 566 | 0.857394366197 | 1 | 0.870675181028 | 0.23630669713 | 17.359375 | 1 | 0.0748057789204 |
| 62 | 3 | 511 | 0.84332688588 | 1 | 0.873701989732 | 0.487926989794 | 15.375 | 1 | 0.0749383712011 |
| 63 | 3 | 539 | 0.871086556169 | 1 | 0.877009449038 | 0.53095215559 | 15.859375 | 1 | 0.0746344329318 |

## Evidence Gaps

- Initial tensor gap: initial weights were not retained; checkpoint 1 has no parameter delta.
- Alignment: chunk n rows precede optimizer update n+1; checkpoint n+1 follows it.
- Checkpoint implementation commit is internally consistent; the audit binds its logical execution and registration hash through the terminal manifest.
- No retained counterfactual identifies reward, optimizer, entropy, or intervention causality.

## Bounded Interpretations

- `take_family_candidate_multiplicity_is_a_structural_probability_pressure`
- `recorded_scores_amplify_take_probability_beyond_candidate_multiplicity`
- `candidate_entropy_overstates_action_family_diversity`
- `terminal_greedy_canary_is_take_family_saturated`

## Unresolved

- `candidate_space_objective_causality`
- `entropy_coefficient_or_entropy_target_causality`
- `floor_only_reward_credit_causality`
- `optimizer_dynamics_causality`
- `proposed_correction_effect`

The retained evidence is descriptive. It does not establish reward, optimizer, architecture, or intervention causality and grants no successor execution authority.

## Sources

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `artifact_manifest.json` | 14018 | `4d6184b0cdd88bc59238053ec6b2be0f7a4d2427a2feb2d758da9afd4d21f498` |
| `checkpoints/checkpoint_0001.json` | 4007876 | `c7a021e7e22dc44c3e84155f545db490e2345beaf93a557918ee1884c2df998d` |
| `checkpoints/checkpoint_0002.json` | 3965437 | `2d235156657c823a33a4405f90c58625ba5ff49066100b709fbe1ebe6e3ec593` |
| `checkpoints/checkpoint_0003.json` | 3782345 | `ce7c0c112c0a51d8954e7a247056256ffe3c7dfbd3192e53ac32fed0b357a828` |
| `checkpoints/checkpoint_0004.json` | 3931275 | `8ecbf742b34ee28d3f9fc4affac2e87cae70a7906047845b719b359a6702fc7c` |
| `checkpoints/checkpoint_0005.json` | 4009393 | `6ce9712aacccb60ca8bfc743acad3868d98659be08f3b9e6e551cadd3ca2d716` |
| `checkpoints/checkpoint_0006.json` | 3849526 | `68725a517e0f0094f6a4bc0d9ede5c621ee77b6f920c1a3c03f511aa48df0b66` |
| `checkpoints/checkpoint_0007.json` | 3939968 | `4446913ffff09b0dab7613d770441f1ac16870e6131f68e3dd842ec32d77a1bd` |
| `checkpoints/checkpoint_0008.json` | 3892389 | `b4bcabe88c29333df07ec3be8ef8fd2b2bdf42c4acd146f496f229ffab204559` |
| `checkpoints/checkpoint_0009.json` | 4030921 | `768c46d00a80e3fae91f5ede9eda45af51e99e8ee922cf982b3c85e43d9f4ff6` |
| `checkpoints/checkpoint_0010.json` | 4000022 | `dba2c0e64334bbb25742d9d336dfa255fa1b0f446625ecad417e9a93e0f12022` |
| `checkpoints/checkpoint_0011.json` | 4095516 | `3ee564d4d480014ce9d334495643735c3ab5242317af0f9833461a17ea9fc22f` |
| `checkpoints/checkpoint_0012.json` | 3977178 | `d0cef3a13b77fcba4cd3282904f20a1344ce642aef36ed494760aaba7cdf1ccb` |
| `checkpoints/checkpoint_0013.json` | 4026187 | `8a8fd07d0895a1659313ff9df89e9797e6e245514e01ed0956c617c7c8c884dd` |
| `checkpoints/checkpoint_0014.json` | 4033839 | `db6da0365b5aecc09d2c872553fab3f9b2cb10d406ef7fa18ffb4a14540adb3a` |
| `checkpoints/checkpoint_0015.json` | 4010138 | `ff3d82aec40430dc8643c8f3b268c36011242de78a746083db202239b288e016` |
| `checkpoints/checkpoint_0016.json` | 3915874 | `c064f8e7747fef4300b74bd943d61c59b29bf190809bd996e11cb2d8068151bd` |
| `checkpoints/checkpoint_0017.json` | 4058204 | `a2243dfa735c1dd5b5398057b44c18092b508fc080ffe106c6a3d02624ff7776` |
| `checkpoints/checkpoint_0018.json` | 3888637 | `669069e5d35e09c4809a58439daac65adf5c99047dbd475159ca05491d2be828` |
| `checkpoints/checkpoint_0019.json` | 3800161 | `5c9b6dd55c3aa681fb25e86f6093b22e91104bf23132a8319877ab87e3755473` |
| `checkpoints/checkpoint_0020.json` | 3946582 | `602041a344c25c26c8d75cd7e289c6565d0a87ca1727d55e00276b0f3d4f9189` |
| `checkpoints/checkpoint_0021.json` | 4134876 | `e5306a54703868875455a4510ea72e55c035aeacf9802098588e45e9b8c9d127` |
| `checkpoints/checkpoint_0022.json` | 4009317 | `f5e2ca39a3169e8a388f9de97308fac2590b5f49ab8c31a6997691f471bb8ea2` |
| `checkpoints/checkpoint_0023.json` | 3965984 | `40f5a0f3543d81b8fc3ec1d1c6492be57e6e0c2a881c1db78794c8747eb113f9` |
| `checkpoints/checkpoint_0024.json` | 3939407 | `e1683812955845748d0bb83aa82d4995272f87d8f92da805633e465e49e93409` |
| `checkpoints/checkpoint_0025.json` | 3869903 | `09fab38ce540d90501a37360df328bbd15323ebd79c2a6b084b502a51660dcc4` |
| `checkpoints/checkpoint_0026.json` | 3871729 | `ae01ee245abe9777df694f1f9f63acc282acf3e3fd7cc71e8809bfd7aee99466` |
| `checkpoints/checkpoint_0027.json` | 4183111 | `02839b8fe0c30102050b00486a90038d8aaf07e364c6ffc82c8a27726333261e` |
| `checkpoints/checkpoint_0028.json` | 4061469 | `5f6fe5731f4356818356521899f42749248059ae61ba1f5e2d303521aa4851af` |
| `checkpoints/checkpoint_0029.json` | 4100904 | `bfd4dc8069994e2e2ee88c768efd98e600fe77232adafe5f81721b7fbe76da44` |
| `checkpoints/checkpoint_0030.json` | 4028238 | `72163a961a36818e8a898ed848ca3ce88e8e6e144d5cfac980d36ddecea6598f` |
| `checkpoints/checkpoint_0031.json` | 4093066 | `d333873f61e1ffb1fbf3a6298655a2b19f7962359dac5e62a8ea8149939d4441` |
| `checkpoints/checkpoint_0032.json` | 3930971 | `524d9c7f6470434dfa5f4af94f4dc870b76b5aa7f44ea870b2e77fbd00681275` |
| `checkpoints/checkpoint_0033.json` | 4039671 | `6428db0389584fd8bb84f32d5cb7b7c6dbc7900eba4d01080a87e6998f6e94ce` |
| `checkpoints/checkpoint_0034.json` | 3983449 | `a5cc1b653553cc8076146672c3acc3214429450f84edd11f3760bbfa176acd93` |
| `checkpoints/checkpoint_0035.json` | 3968468 | `95b25d6f42f04ad820d3e501948d6d8a5c492b50f3102183b00e6c9950f85299` |
| `checkpoints/checkpoint_0036.json` | 3965064 | `022056833f9d4e7734d62ac1ac2c17e00e4aa2cef9620aab78b56151d7941524` |
| `checkpoints/checkpoint_0037.json` | 3997665 | `e481eb1445b69bd4977507e65057be01dfc1ad6c00cb62564d02bd0b5ea051f4` |
| `checkpoints/checkpoint_0038.json` | 3971958 | `03487c6e4e56220026b9a5fa007302ddeb477c13ed26f504a9c9abf2f0f0f6fc` |
| `checkpoints/checkpoint_0039.json` | 4123994 | `e7675081371f8ba37f83ea4a56f05a695871a65a2c3207e3c9dfce736e357783` |
| `checkpoints/checkpoint_0040.json` | 3996300 | `a150582df3ee1b7f005690bf72408eaa89061eb8055d3e0128f8bdd3112733b1` |
| `checkpoints/checkpoint_0041.json` | 4027643 | `343e0055630c4f630874dfe54f453da2c432d0b95cbbb75de9f684cc44407235` |
| `checkpoints/checkpoint_0042.json` | 4054117 | `4a2181c869c92e9f0a35cf564c29eabe74aa0ac283ae4e03530ab2dc05098a91` |
| `checkpoints/checkpoint_0043.json` | 4123338 | `8eb8ddaba2282784bdcb706cb40dea46b263ec6c60541de597a0fac21b2392ba` |
| `checkpoints/checkpoint_0044.json` | 3866948 | `568936c4ca244f4861cba9b351607feb5ea05a891c15037c33419ebcf7b40139` |
| `checkpoints/checkpoint_0045.json` | 4061593 | `970034daf4f8086be3dbd18947387ef154e387fc862a08a9c407bd7c5aefa530` |
| `checkpoints/checkpoint_0046.json` | 3919011 | `a628d143fb4abc45d280c390472194a92be15ecdaed563e7e844da2517c2d7b4` |
| `checkpoints/checkpoint_0047.json` | 4292107 | `8655efc620f8359ce12e57b940d3963d63441e86b26dfe352be463e49f464911` |
| `checkpoints/checkpoint_0048.json` | 4249138 | `cc49c27107236b79151d71bedb02df86da846d70bd11ab5ecfb284b9e2249167` |
| `checkpoints/checkpoint_0049.json` | 4218707 | `cbe7d8c4f541527695f7b2a6c9d4e40a61dd9225467bf9faf9082fc231736671` |
| `checkpoints/checkpoint_0050.json` | 4042605 | `6c00d8e59359620cc693020b8fdff49ebfaa8a0215b4b1a3f238bb57254ad41d` |
| `checkpoints/checkpoint_0051.json` | 4096916 | `684cd423e3720cd8190c778f0aad20cbdba6ebca7ce96eafa71ef30b641221a3` |
| `checkpoints/checkpoint_0052.json` | 4222108 | `de778705d287242566842b67cc4a2d1482d2e92fd47c5b6f85a5c0978030e813` |
| `checkpoints/checkpoint_0053.json` | 4116425 | `dd3c3955086c43a5c645766313462a3db00b13df4b0693692cba342dca8e51db` |
| `checkpoints/checkpoint_0054.json` | 4088821 | `5ce693dfd098ddf0b1e4f88217eb0f319a554b098c4ac51400146f126692c941` |
| `checkpoints/checkpoint_0055.json` | 4088773 | `b6c73698829203e19b36d8d6654cf56f7bd9988ff9f625305f68e73a84b0c8ef` |
| `checkpoints/checkpoint_0056.json` | 4160348 | `7410d42bac45fa79bb54de136119ef08855c740c7f84421ce50b2ab749d21880` |
| `checkpoints/checkpoint_0057.json` | 4077310 | `9fd2c3d9918c01c98740d38cfa8583d359339e9fd639bf49bfce923df9ad374e` |
| `checkpoints/checkpoint_0058.json` | 4106366 | `10eb8d42476a286c3e2f4953c429835427cfd46e7a268ea015e1397f5dbbce8e` |
| `checkpoints/checkpoint_0059.json` | 4197505 | `7ec32000712a325f1c76a182db3725269112ea22aad018e7aa424c3314e67c49` |
| `checkpoints/checkpoint_0060.json` | 4051193 | `958059232289e9d1083eb8519fced4a0361bb1e9c5dcb9a9b1fdbdd21d6f51cf` |
| `checkpoints/checkpoint_0061.json` | 4210605 | `d2b765bb600d81eb93247a31b08487b1c19b1019a1869f52671147d39aff06e2` |
| `checkpoints/checkpoint_0062.json` | 4482632 | `e891dd8c9d712d3e7d7b037ab9bd4624dca9ea542c4458e87df178d7532ff414` |
| `checkpoints/checkpoint_0063.json` | 4188733 | `fa6f76e1c79260ea094e481ff6f090ecba5b12e7c70ce17b08615991b8b971b1` |
| `checkpoints/checkpoint_0064.json` | 4266354 | `c7eb4d78ea0b0d565a072948689e2e6a928e811420ac3f3a83827b9364fd3ad2` |
| `diagnostics.json` | 30841 | `d11fadb6a3c2a7bf1b3fdc7c92af6241b70dc1a91c6d95b648221e4a60a5b689` |
| `evaluation.json` | 20492084 | `bf76b4684e9c993c0fe6527d02e0c889521449bf525fabe8d36d2bd119042579` |
| `final_model.json` | 701964 | `b24cc22b8e5456e3384d3572c0a1ab19cdaba1d58b3e04c52e82e1ff0b048bad` |
| `metrics.json` | 1323 | `0da5ad0c004b806c2e1223c6a3b0f556a7f9c719f5c235e13a475203eefc6e47` |
| `training_rows.json` | 126834076 | `1d19779b44ff5c8b2ea598307017af7b892b8b875395e22feb4b3d4eb5061eea` |

## Invocation

```json
["D:\\anaconda\\envs\\stsai\\python.exe", "D:\\PycharmProjects\\slay-the-spire-ai\\analysis_scripts\\noncombat_state_conditioned_collapse_audit.py", "--source", "D:\\PycharmProjects\\slay-the-spire-ai\\reports\\noncombat_state_conditioned_simulator_learning_experiment_20260805", "--output-json", "D:\\PycharmProjects\\slay-the-spire-ai\\reports\\noncombat_state_conditioned_card_reward_collapse_audit_20260805.json", "--output-markdown", "D:\\PycharmProjects\\slay-the-spire-ai\\reports\\noncombat_state_conditioned_card_reward_collapse_audit_20260805.md"]
```
