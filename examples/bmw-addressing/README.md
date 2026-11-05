# ISO-TP extended and mixed addressing

BMW-style diagnostics: every ECU listens on `6F1`, the tester is `F1`, and each ECU answers on `600` plus its own address. The address byte in front of every PCI is ISO 15765-2 extended addressing, not a BMW-specific transport. `body` shows mixed addressing, where one address extension travels in both directions.

The package declares no `channels` and no endpoint `channel`, so both endpoints resolve to the default channel `can0`, classic CAN at 500 kbit/s on OBD pins 6 and 14. Requests and response patterns are application bytes; the adapter inserts and strips the address byte and the PCI. The `VIN` request goes out as `6F1: 12 03 22 F1 90 00 00 00`. Nothing here is physical test evidence.
