## Context

The r1 static coverage audit binds exact Current and `sts_lightspeed` source
bytes, but its C++ case summaries run regexes over raw case text. The case
indexer ignores lines beginning with `//` when finding case labels, yet
`summarize_display_case`, `summarize_legal_case`,
`summarize_execution_case`, and `_case_summary_base` still inspect comments
inside the selected span. This admitted four known false display entries from
commented-out console code.

The correction must preserve raw source provenance, line spans, the immutable
r1 result, and all no-execution authority boundaries. It must not broaden into
a general C++ parser or use a native simulator run to discover labels.

## Goals / Non-Goals

**Goals:**

- Make comment handling deterministic and aware of ordinary C++ strings,
  character literals, line comments, and block comments.
- Preserve source length and newline positions so masked analysis has the same
  offsets and line numbers as the registered raw source.
- Keep raw case text as the source-hash input while using only masked text for
  case discovery and semantic summaries.
- Publish one fresh r2 registration and prove its exact delta from r1.

**Non-Goals:**

- Parsing arbitrary C++ syntax or evaluating dynamic expressions.
- Changing the event resolver, adapter, Current policy, or upstream checkout.
- Running native simulator episodes, any seed, gameplay, model fitting, reward
  design, or training.
- Rewriting or deleting r1 artifacts.

## Decisions

### Use a layout-preserving lexical masker

Replace comment bytes with spaces while preserving every newline and leaving
ordinary string and character literals unchanged. The masker tracks escapes
and fails on unterminated comments or literals. Unsupported raw-string syntax
fails closed rather than being interpreted by regex.

Alternative considered: reuse the current two-regex `_strip_cpp_comments`.
Rejected because it removes bytes and lines, does not respect comment markers
inside literals, and can corrupt registered source offsets.

### Separate raw provenance from semantic analysis

`index_cpp_event_cases` will locate signatures, braces, and case labels on the
masked projection. Each indexed case retains both exact raw `text` and an
equal-layout internal analysis span. Raw text remains the input to
`source_sha256`; condition, phase, return, display, and effect extraction uses
only the masked span.

Alternative considered: store only stripped text and hash it. Rejected because
comments are still part of the exact registered source and removing them from
the case hash would weaken provenance.

### Publish a new immutable r2 result

The parser fix is committed before registration. A new registration binds that
commit and implementation hash while keeping Current, upstream, canonical
event registry, and all authority unchanged. It writes to an r2 output
directory and is executed once plus one strict recomputation.

An explicit delta check requires unchanged event, alias, status, unaccounted
alias, resolver-readiness, and authority values. The expected semantic delta is
removal of `Big Fish` entry `0: Offer` and `Cursed Tome` entries `0: Continue`,
`0: Take`, and `1: Stop`; any other row-level change requires a new review.

## Risks / Trade-offs

- **Unsupported C++ literal syntax appears later** -> Fail with a named parser
  blocker and require a focused extension; do not silently fall back.
- **Masking changes line layout** -> Test equal byte length and identical
  newline offsets for every fixture and real source.
- **A correction unexpectedly changes coverage status** -> Block r2
  publication through an exact predecessor-delta check.
- **r1 is mistaken for current evidence** -> Mark it superseded in the r2
  closeout and project direction without mutating its files.
