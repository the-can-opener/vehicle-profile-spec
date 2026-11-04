# Nissan Versa migration example

Reproduce with `python scripts/migrate-versa.py` from the repository root.
The script declares `--framing isotp-single-frame --steering-side left` for the retained legacy input. It removes validated single-frame PCI and padding from request/response commands and retains the original application response patterns, including wildcards. The request-only ECU_WAKE and WIPERS commands remain byte-exact raw CAN. The original DBC and complete format 1 input remain under `../legacy/nissan-versa-1-6`.

These declarations describe the source framing and left-hand-drive mapping; they are not physical test evidence. DBC comments identify Sentra-derived observations. Do not infer model-year compatibility from the package metadata. TPS has no established canonical mapping and the fractional steering decoder does not preserve the VSS integer datatype; both remain in unmapped with the original data.

The 2011 overlay is **synthetic**: it inserts a 10 ms wait in the shared setup sequence to demonstrate late call resolution and narrower applicability. It claims no real 2011 ECU difference. Compare exports with `--vehicle make=Nissan,model=Versa,year=2008` and `year=2011`.

LOCK/UNLOCK control all doors and remain actions. HORN supports only the true case. Fixture expectations preserve the legacy application bytes; no raw receive PCI values are invented. Runtime execution and vehicle testing are outside this repository.
