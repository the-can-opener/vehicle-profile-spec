# Synthetic dual-bus CAN FD

All addresses and payloads are illustrative. The package declares two logical channels: `can0` is classic CAN at 500 kbit/s, and `can1` is a CAN FD channel whose nominal bitrate the runtime detects (`auto`) with a 2 Mbit/s data phase. Requests on `can1` default to CAN FD with 64-byte ISO-TP frames; `bcm` keeps 8-byte ISO-TP frames and `legacy-ecu` stays classic. `obd` accepts a range of response IDs and selects `7E8`. A runtime maps `can0` and `can1` to its own controllers; the names are not host interfaces.
