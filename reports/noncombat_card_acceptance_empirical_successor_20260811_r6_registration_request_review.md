# R6 Registration Request Review

- Request: `reports/noncombat_card_acceptance_empirical_successor_20260811_r6_registration_request.json`
- Canonical size: `3196` bytes
- File SHA-256: `ec7c687178e74fb9a9ff984c328115edd43959c6551bad63ab3811342558b198`
- Body/self SHA-256: `073f84db8391ea5643f0bb112e85ef4540cbc4297caff9dab520b3b64079aced`
- Pushed preflight SHA-256: `2486fe6c00749ed34788c1e4965fe53e64e858b27f1f8b7cbde088738a9115c4`
- Review scope: exact canonical preflight and request plus bounded replay ledger
- Reviewer access: tools and path access prohibited; no repository or report-root search
- Reviewer verdict: `No findings.`

The replay confirmed exact equality between the request input bindings and the
six preflight evidence bindings, exact receipt/output paths, frozen source and
registration identities, and the all-false downstream map. Request rendering
and review did not open an r5 evidence input or invoke the registration driver.

The sole reviewed command is:

```text
D:/anaconda/envs/stsai/python.exe -I D:/PycharmProjects/slay-the-spire-ai/analysis_scripts/noncombat_card_acceptance_empirical_successor_registration.py publish-registration --repo-root D:/PycharmProjects/slay-the-spire-ai --request D:/PycharmProjects/slay-the-spire-ai/reports/noncombat_card_acceptance_empirical_successor_20260811_r6_registration_request.json --expected-request-sha256 073f84db8391ea5643f0bb112e85ef4540cbc4297caff9dab520b3b64079aced --receipt-path D:/PycharmProjects/slay-the-spire-ai/reports/noncombat_card_acceptance_empirical_successor_20260811_r6_registration_started.json
```
