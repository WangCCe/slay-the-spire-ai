# V2 R6 Qualification Outcome

Date: 2026-07-18

Status: retired pre-request launcher timeout; no active request, handshake, terminal, study artifact, gameplay evidence, or launch authority.

## Reviewed Identity

| Field | Value |
|---|---|
| Source snapshot S | `2936c547bd7917fdbbc487470326716129e3fbe2` |
| Direct-child review commit R | `9542af3aae8f93fa29eeaeefabcc5a1860a0107a` |
| R parent | exact S above |
| R changed paths | exact seven-path request allowlist |
| Request self-hash | `fc5332ffca8b00a1e5132047d07538825369f187db030d9e080a91d37fa8496c` |
| Request file SHA-256 | `28c174d6fba875ba110b107c92da5d522664ead81d9bf5c0db71db6fc3748b69` |
| Request size | 8886 bytes |
| Source-only verifier | 95 checks, `passed=true`, `status=reviewed_prepared`, audit hash `938d603a13601717f26c92684e88ca35a32ec6baff51757a0351de3cb36c48a0` |

R was pushed to `origin/codex/noncombat-ope-readiness` before launch. Tracked source was clean, `HEAD == R`, all 14 implementation files matched S and the request, the registered study root was absent, and no target Python or Java process existed.

Historical replay matched all fixed anchors: r1-r3 failure-record self-hashes, file SHA-256 values, final root inventories, and closed authority; r4/r5 request hashes and static-only roots; and the r5 95-check source-only review chain. The R-bound 24-launch dry-run used source commit R in all slot configs and had canonical LF SHA-256 `00bdc60e50d0812b00d8c2b8349466ec0e4d6eea3388908eef80672b19043eb9`, size 57941 bytes.

## One Live Invocation

The pre-Java launch configuration contained exactly 20 trusted-launcher tokens, preserved all non-command properties including `maxInitializationTimeout=120`, and passed the full request-bound prelaunch isolation check.

| Observation | SHA-256 | Bytes |
|---|---|---:|
| Rendered launch configuration before Java load | `38f4383addc15305049e4427e54f006f4d0b2ddfc27585d8a159bcfaeabe7144` | 3165 |
| Java-rewritten launch configuration after timeout | `2bb394139bf96e28cecbb402a5aeb6504f952a1a49be20aa24b162a063772248` | 3166 |
| Request-bound r6 baseline restored after cleanup | `a404525790c925423d6298b639322b370ccf37414f9808362bd24a8dc9feb202` | 535 |

Java's rewritten file parsed back to the same 20 command tokens and the same five semantic properties. One ModTheSpire process started at approximately 14:04 local time. At `06:06:44.321` in `SlayTheSpire.log`, exactly 120 seconds after CommunicationMod initialization began, CommunicationMod reported `Timed out while waiting for signal from external process.` It then killed the silent external process. No second launch occurred.

The r6 root never advanced beyond its original `qualification-config.json`, SHA-256 `b1b734e885ba7404e5492bb8911be97494eab789ddb21c0fb6230f46d3161404`, size 949. The active request, attempt, ready, release, completion, failure, manifest, trace, registered study root, run lock, and ledger remained absent. Therefore this is not a protocol failure terminal and cannot be attested as a qualification result.

## Cleanup And Isolation

After the external process was already dead, the visible game was at the main menu. The diagnostic screenshot and exact post-timeout configuration were preserved outside the repository. Java was stopped without relaunch, the exact 535-byte r6 baseline was restored atomically, and the request-bound isolation observation replayed with zero mismatches:

- observation hash `7ce9e3507eaf8bcbc1ddecbe151b0a3525b266fd1a12ee88a0fbae08e00acbe7`
- marker 15255 lines
- recursive runs inventory 1365 entries
- registered checkpoint inventory 208 entries
- unchanged `ai_debug.log` and `communication_mod_errors.log`
- no target Python, Java, or Slay the Spire process
- registered study root absent

External diagnostic evidence is under `D:\PycharmProjects\slay-the-spire-ai-test-artifact-quarantine\20260718-r6-pre-request-no-terminal`:

| File | SHA-256 | Bytes |
|---|---|---:|
| `communication-config-observed-after-timeout.properties` | `2bb394139bf96e28cecbb402a5aeb6504f952a1a49be20aa24b162a063772248` | 3166 |
| `SlayTheSpire-r6-pre-request-timeout.log` | `597660e40789c51b8d07db8a992a438d021e5c3d85f06ea8b0a2317e651594ac` | 18108 |
| `sts_screen_20260718_141103_560.png` | `4b97697b8764b1b091eea8a0822129560a3fe8d137f4cc2786badf4cfccda0cf` | 1198658 |

## Supported Diagnosis

The only live-supported stage boundary is: CommunicationMod successfully created an external process, received no `ready` within 120 seconds, killed it, and the process never published the active request. The exact internal stage between trusted launcher entry and request publication is not observable in r6 and must not be inferred from later offline timing.

Two bounded offline probes narrowed but did not resolve that stage:

- the trusted bootstrap-only path completed in 1.898 seconds and exited silently as expected on intentionally incomplete arguments
- canonical request-source review plus the repeated R-chain validation completed in 6.688 and 6.459 seconds, respectively

No matching Windows Security, Application, or System event preserved a Python exit/crash reason. These offline results reject a simple claim that the reviewed bootstrap necessarily requires more than 120 seconds, but they do not prove what the live process did.

## Authority

R6 is immutable and may not be retried, pooled, or reinterpreted as a passing or failed protocol terminal. Collection, `start`, run-lock creation, OPE interpretation, causal claims, gameplay-policy changes, formal training, and promotion remain unauthorized.

The next implementation work must be a separate reviewed change that makes the pre-request lifecycle durably and independently diagnosable without weakening source binding, request binding, isolation, one-shot identity, restoration, or the closed authority boundary. A new qualification root may be prepared only after that repair or an equivalent explicit evidence-backed amendment.
