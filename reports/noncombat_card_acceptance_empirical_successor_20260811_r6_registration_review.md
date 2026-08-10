# R6 Registration Publication Review

- Registration id: `noncombat-card-acceptance-empirical-successor-20260811-r6-registration-v1`
- Unique driver invocation: exit `0`; no retry or replacement
- Receipt file SHA-256: `31a57e1fbfc19b5bacab832e2423143eec13ee5bc3eedab3db9bdc57221496d8`
- Receipt self SHA-256: `26e1e88a0b343e1ea7b528fce15c2d87cae1bcae274310c569bc41fe68fadfa4`
- Registration file SHA-256: `ec1cef4261a2820a058b6cfe79c4b090b94787acf4ba9fc5ef9f2d47ac41b929`
- Registration self SHA-256: `1f66f434230dec8edfaeb3e04062d97164543d1d337a12ba3051891896f9b204`
- Producer validation: `true`
- Independent standalone validation: `true`
- Request access count: `1`
- Evidence access counts: exactly one for each of the six allowlisted inputs
- Registration schema: exact `16` fields
- Authority and empirical-operation maps: exact and all false
- Surviving registration-driver processes: `0`
- Bounded tool-prohibited reviewer verdict: `No findings.`

An outer launch check initially stopped before process creation because its
locally asserted request-publication commit used an incorrect expanded SHA.
No receipt or output existed and the driver identity was not consumed. The
check was corrected to the actual pushed HEAD without changing the request,
CLI, source, evidence bindings, thresholds, or paths; the reviewed driver was
then invoked exactly once.

The exact driver completion was:

```json
{"access_counts":{"build_receipt":1,"inventory":1,"standalone_result":1,"verification_completion":1,"verification_receipt":1,"verification_review":1},"completion_schema_version":"noncombat-card-acceptance-empirical-successor-registration-completion-v1","output_sha256":"ec1cef4261a2820a058b6cfe79c4b090b94787acf4ba9fc5ef9f2d47ac41b929","producer_validated":true,"receipt_sha256":"26e1e88a0b343e1ea7b528fce15c2d87cae1bcae274310c569bc41fe68fadfa4","registration_sha256":"1f66f434230dec8edfaeb3e04062d97164543d1d337a12ba3051891896f9b204","request_access_count":1,"standalone_validated":true}
```

This publication completes parent task 6.2 only. Parent task 6.3 remains
incomplete. No training request, execution authority, native/model loading,
environment construction, gameplay, evaluation, OPE, qualification, promotion,
or other downstream authority was created.
