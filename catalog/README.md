# Pinned VSS catalog

`vss-6.1.json` is the full expanded COVESA Vehicle Signal Specification v6.1 export, generated from tag `v6.1`, commit `2817646d1808fc7c470c0432fc7f4ed685e5c9e3` in `https://github.com/COVESA/vehicle_signal_specification`.

Run `make catalog VSS_SOURCE=/path/to/vehicle_signal_specification`. The script verifies the tag commit, exports that tree into temporary storage, and runs `vss-tools==1.9.9` / `vspec export json --strict` with the release units file. It never depends on the source checkout's working tree or branch. The catalog is bundled into the Python wheel so lookups work outside this repository. Source license and notice are included alongside the data.
