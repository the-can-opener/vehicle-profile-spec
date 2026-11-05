# Keyword vocabulary

[Overview](../README.md) · [Documentation index](README.md)

Generated from [vocabulary.yaml](vocabulary.yaml); do not edit this listing by hand.

| Keyword | Mapping | Unit | Write target | Notes |
|---|---|---|---|---|
| `ACTUAL_TORQUE` | `Vehicle.Powertrain.CombustionEngine.Torque` | Nm |  | Current engine torque. |
| `ACTUATE_TRUNK_FRONT` | action `ACTUATE_TRUNK_FRONT` |  |  |  |
| `ACTUATE_TRUNK_REAR` | action `ACTUATE_TRUNK_REAR` |  |  |  |
| `ADD_CHARGE_SCHEDULE` | action `ADD_CHARGE_SCHEDULE` |  |  |  |
| `ADD_PRECONDITION_SCHEDULE` | action `ADD_PRECONDITION_SCHEDULE` |  |  |  |
| `AUTO_CONDITIONING_START` | action `AUTO_CONDITIONING_START` |  |  |  |
| `AUTO_CONDITIONING_STOP` | action `AUTO_CONDITIONING_STOP` |  |  |  |
| `BARO` | `Vehicle.OBD.BarometricPressure` | kPa |  | COVESA OBD overlay, PID 33. |
| `BATTERY_LEVEL` | `Vehicle.Powertrain.TractionBattery.StateOfCharge.Displayed` | percent |  | Customer-displayed state of charge. Physical state of charge is StateOfCharge.Current. |
| `BATTERY_RANGE` | `Vehicle.Powertrain.TractionBattery.Range` | m |  | Battery-only remaining range. |
| `BRAKE_LIGHTS` | `Vehicle.Body.Lights.Brake.IsActive` |  |  |  |
| `CABIN_TEMP` | `Vehicle.Cabin.HVAC.AmbientAirTemperature` | Celsius |  |  |
| `CANCEL_SOFTWARE_UPDATE` | action `CANCEL_SOFTWARE_UPDATE` |  |  |  |
| `CHARGER_CURRENT` | `Vehicle.Powertrain.TractionBattery.Charging.ChargeCurrent.DC` | A |  | DC inlet current. AC current is Phase1, Phase2, and Phase3. |
| `CHARGER_POWER` | `Vehicle.Powertrain.TractionBattery.Charging.AveragePower` | kW |  | Average power of the current or last charging event. |
| `CHARGER_VOLTAGE` | `Vehicle.Powertrain.TractionBattery.Charging.ChargeVoltage.DC` | V |  | DC inlet voltage. AC voltage is Phase1, Phase2, and Phase3. |
| `CHARGE_ENERGY_ADDED` | unmapped |  |  | Session energy added has no VSS signal. Vehicle.Powertrain.TractionBattery.AccumulatedChargedEnergy is lifetime charged energy. |
| `CHARGE_LIMIT_SOC` | `Vehicle.Powertrain.TractionBattery.Charging.ChargeLimit` | percent |  |  |
| `CHARGE_PORT_CLOSE` | `Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.AnyPosition.IsFlapOpen` |  | `false` | Single charging port. Use a position instance instead of AnyPosition when the port location is known. |
| `CHARGE_PORT_OPEN` | `Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.AnyPosition.IsFlapOpen` |  | `true` | Single charging port. Use a position instance instead of AnyPosition when the port location is known. |
| `CHARGE_RATE` | `Vehicle.Powertrain.TractionBattery.Charging.ChargeRate` | km/h |  |  |
| `CHARGE_START` | `Vehicle.Powertrain.TractionBattery.Charging.StartStopCharging` |  | `"START"` |  |
| `CHARGE_STOP` | `Vehicle.Powertrain.TractionBattery.Charging.StartStopCharging` |  | `"STOP"` |  |
| `CHARGING_STATE` | unmapped |  |  | disconnected, stopped, charging, and complete do not match Vehicle.Powertrain.TractionBattery.ChargingState. |
| `CLIMATE_OFF` | unmapped |  |  | No single climate power actuator. Air conditioning is Vehicle.Cabin.HVAC.IsAirConditioningActive. |
| `CLIMATE_ON` | unmapped |  |  | No single climate power actuator. Air conditioning is Vehicle.Cabin.HVAC.IsAirConditioningActive. |
| `CLOSE_FRONT_LEFT_WINDOW` | `Vehicle.Cabin.Door.Row1.DriverSide.Window.Position` | percent | `0` | Left/right mapping assumes left-hand-drive; review vehicle applicability. 0 is fully closed. |
| `CLOSE_FRONT_RIGHT_WINDOW` | `Vehicle.Cabin.Door.Row1.PassengerSide.Window.Position` | percent | `0` | Left/right mapping assumes left-hand-drive; review vehicle applicability. 0 is fully closed. |
| `CLOSE_FRUNK` | `Vehicle.Body.Trunk.Front.IsOpen` |  | `false` | Front luggage compartment. Vehicle.Body.Hood is the engine cover. |
| `CLOSE_REAR_LEFT_WINDOW` | `Vehicle.Cabin.Door.Row2.DriverSide.Window.Position` | percent | `0` | Left/right mapping assumes left-hand-drive; review vehicle applicability. 0 is fully closed. |
| `CLOSE_REAR_RIGHT_WINDOW` | `Vehicle.Cabin.Door.Row2.PassengerSide.Window.Position` | percent | `0` | Left/right mapping assumes left-hand-drive; review vehicle applicability. 0 is fully closed. |
| `CLOSE_TRUNK` | `Vehicle.Body.Trunk.Rear.IsOpen` |  | `false` |  |
| `DEFROST_OFF` | `Vehicle.Cabin.HVAC.IsFrontDefrosterActive` |  | `false` | Front defroster. Rear defroster is Vehicle.Cabin.HVAC.IsRearDefrosterActive. |
| `DEFROST_ON` | `Vehicle.Cabin.HVAC.IsFrontDefrosterActive` |  | `true` | Front defroster. Rear defroster is Vehicle.Cabin.HVAC.IsRearDefrosterActive. |
| `DIST_SINCE_CLEAR` | `Vehicle.OBD.DistanceSinceDTCClear` | km |  | COVESA OBD overlay, PID 31. |
| `DRIVER_TEMP_SETTING` | `Vehicle.Cabin.HVAC.Station.Row1.Driver.Temperature` | Celsius |  |  |
| `DRIVER_TORQUE_DEMAND` | unmapped |  |  | OBD driver-demand engine torque (PID 61) is not in the VSS 6.1 catalog or the OBD overlay. |
| `ECT` | `Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature` | Celsius |  |  |
| `ECU_WAKE` | action `ECU_WAKE` |  |  |  |
| `ENGINE_LOAD` | `Vehicle.OBD.EngineLoad` | percent |  | COVESA OBD overlay, PID 04. |
| `ESTIMATED_RANGE` | `Vehicle.Powertrain.Range` | m |  | Remaining range from all energy sources. |
| `FRONT_LEFT_DOOR` | `Vehicle.Cabin.Door.Row1.DriverSide.IsOpen` |  |  | Closed and open. Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `FRONT_LEFT_DOOR_OPEN` | `Vehicle.Cabin.Door.Row1.DriverSide.IsOpen` |  | `true` | Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `FRONT_RIGHT_DOOR` | `Vehicle.Cabin.Door.Row1.PassengerSide.IsOpen` |  |  | Closed and open. Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `FRONT_RIGHT_DOOR_OPEN` | `Vehicle.Cabin.Door.Row1.PassengerSide.IsOpen` |  | `true` | Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `FUEL_LEVEL` | `Vehicle.Powertrain.FuelSystem.RelativeLevel` | percent |  |  |
| `FUEL_PRESSURE` | `Vehicle.OBD.FuelPressure` | kPa |  | COVESA OBD overlay, PID 0A. |
| `FUEL_RATE` | `Vehicle.OBD.FuelRate` | l/h |  | Engine fuel rate. COVESA OBD overlay, PID 5E. FuelSystem.InstantConsumption is l/100km. |
| `GEAR` | `Vehicle.Powertrain.Transmission.SelectedGear` |  |  | Selected gear. 126 = park, -1 = reverse, 0 = neutral, 127 = drive. |
| `HAZARD_LIGHTS` | `Vehicle.Body.Lights.Hazard.IsSignaling` |  | `true` |  |
| `HIGH_BEAM` | `Vehicle.Body.Lights.Beam.High.IsOn` |  | `true` |  |
| `HIGH_BEAMS` | `Vehicle.Body.Lights.Beam.High.IsOn` |  | `true` |  |
| `HORN` | `Vehicle.Body.Horn.IsActive` |  | `true` |  |
| `IAT` | `Vehicle.OBD.IntakeTemp` | Celsius |  | COVESA OBD overlay, PID 0F. |
| `IDEAL_RANGE` | unmapped |  |  | VSS has no ideal or rated range separate from remaining range. |
| `LAMBDA` | `Vehicle.OBD.O2WR.Sensor1.Lambda` |  |  | First wideband oxygen sensor, PID 24. Sensors 2 through 8 are Vehicle.OBD.O2WR.Sensor2.Lambda through Sensor8.Lambda. |
| `LEFT_SIGNAL` | `Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling` |  | `true` |  |
| `LOCK` | `Vehicle.Cabin.IsCentralLockEngaged` |  | `true` |  |
| `LOCKED` | `Vehicle.Cabin.IsCentralLockEngaged` |  |  |  |
| `LOW_BEAM` | `Vehicle.Body.Lights.Beam.Low.IsOn` |  | `true` |  |
| `LOW_BEAMS` | `Vehicle.Body.Lights.Beam.Low.IsOn` |  | `true` |  |
| `LTFT_B1` | `Vehicle.OBD.LongTermFuelTrim1` | percent |  | COVESA OBD overlay, PID 07. |
| `LTFT_B2` | `Vehicle.OBD.LongTermFuelTrim2` | percent |  | COVESA OBD overlay, PID 09. |
| `MAF` | `Vehicle.Powertrain.CombustionEngine.MAF` | g/s |  |  |
| `MAP` | `Vehicle.Powertrain.CombustionEngine.MAP` | kPa |  |  |
| `MIL_STATUS` | `Vehicle.OBD.Status.IsMILOn` |  |  | Malfunction indicator lamp. COVESA OBD overlay, PID 01. |
| `MODULE_VOLTAGE` | `Vehicle.OBD.ControlModuleVoltage` | V |  | COVESA OBD overlay, PID 42. |
| `O2_DATA` | `Vehicle.OBD.O2.Sensor1.Voltage` | V |  | First narrowband sensor voltage, PID 14 byte A. Short-term trim is Vehicle.OBD.O2.Sensor1.ShortTermFuelTrim. Sensors 2 through 8 follow the same shape. |
| `ODOMETER` | `Vehicle.TraveledDistance` | m |  | Lifetime distance. |
| `OIL_TEMP` | `Vehicle.Powertrain.CombustionEngine.EngineOil.Temperature` | Celsius |  |  |
| `OPEN_FRONT_LEFT_WINDOW` | `Vehicle.Cabin.Door.Row1.DriverSide.Window.Position` | percent | `100` | Left/right mapping assumes left-hand-drive; review vehicle applicability. 100 is fully open when the command does not select a percent. |
| `OPEN_FRONT_RIGHT_WINDOW` | `Vehicle.Cabin.Door.Row1.PassengerSide.Window.Position` | percent | `100` | Left/right mapping assumes left-hand-drive; review vehicle applicability. 100 is fully open when the command does not select a percent. |
| `OPEN_FRUNK` | `Vehicle.Body.Trunk.Front.IsOpen` |  | `true` | Front luggage compartment. Vehicle.Body.Hood is the engine cover. |
| `OPEN_REAR_LEFT_WINDOW` | `Vehicle.Cabin.Door.Row2.DriverSide.Window.Position` | percent | `100` | Left/right mapping assumes left-hand-drive; review vehicle applicability. 100 is fully open when the command does not select a percent. |
| `OPEN_REAR_RIGHT_WINDOW` | `Vehicle.Cabin.Door.Row2.PassengerSide.Window.Position` | percent | `100` | Left/right mapping assumes left-hand-drive; review vehicle applicability. 100 is fully open when the command does not select a percent. |
| `OPEN_TRUNK` | `Vehicle.Body.Trunk.Rear.IsOpen` |  | `true` |  |
| `OUTSIDE_TEMP` | `Vehicle.Exterior.AirTemperature` | Celsius |  |  |
| `PASSENGER_TEMP_SETTING` | `Vehicle.Cabin.HVAC.Station.Row1.Passenger.Temperature` | Celsius |  |  |
| `PLUGGED_IN` | `Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.AnyPosition.IsChargingCableConnected` |  |  | Single charging port. Use a position instance instead of AnyPosition when the port location is known. |
| `READINESS_STATUS` | unmapped |  |  | OBD readiness monitors are a bitmap in PID 01 and are not a single signal. MIL state is Vehicle.OBD.Status.IsMILOn. |
| `REAR_LEFT_DOOR` | `Vehicle.Cabin.Door.Row2.DriverSide.IsOpen` |  |  | Closed and open. Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `REAR_LEFT_DOOR_OPEN` | `Vehicle.Cabin.Door.Row2.DriverSide.IsOpen` |  | `true` | Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `REAR_RIGHT_DOOR` | `Vehicle.Cabin.Door.Row2.PassengerSide.IsOpen` |  |  | Closed and open. Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `REAR_RIGHT_DOOR_OPEN` | `Vehicle.Cabin.Door.Row2.PassengerSide.IsOpen` |  | `true` | Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `REAR_WIPER` | `Vehicle.Body.Windshield.Rear.Wiping.Mode` |  | `"MEDIUM"` | Rear windshield. Use MEDIUM when the command does not select a speed. |
| `REAR_WIPER_OFF` | `Vehicle.Body.Windshield.Rear.Wiping.Mode` |  | `"OFF"` | Rear windshield. |
| `REMOTE_START` | action `REMOTE_START` |  |  |  |
| `REMOVE_CHARGE_SCHEDULE` | action `REMOVE_CHARGE_SCHEDULE` |  |  |  |
| `REMOVE_PRECONDITION_SCHEDULE` | action `REMOVE_PRECONDITION_SCHEDULE` |  |  |  |
| `REVERSE_LIGHTS` | `Vehicle.Body.Lights.Backup.IsOn` |  |  |  |
| `RIGHT_SIGNAL` | `Vehicle.Body.Lights.DirectionIndicator.Right.IsSignaling` |  | `true` |  |
| `RPM` | `Vehicle.Powertrain.CombustionEngine.Speed` | rpm |  |  |
| `RUNNING_LIGHTS` | `Vehicle.Body.Lights.Running.IsOn` |  | `true` |  |
| `RUNTIME` | `Vehicle.OBD.RunTime` | s |  | Engine run time. COVESA OBD overlay, PID 1F. |
| `SCHEDULE_SOFTWARE_UPDATE` | action `SCHEDULE_SOFTWARE_UPDATE` |  |  |  |
| `SEATBELT_WARNING` | `Vehicle.Cabin.IsSeatBeltWarningActive` |  |  | Vehicle seatbelt warning indicator. True means the indicator is active. Per-seat buckle state remains IsBelted. |
| `SET_CHARGE_LIMIT` | unmapped |  |  | The limit is a caller-supplied value, not a fixed write target. The signal is Vehicle.Powertrain.TractionBattery.Charging.ChargeLimit. |
| `SET_CHARGING_AMPS` | unmapped |  |  | No commanded charging-current actuator. MaximumChargingCurrent is inlet capability, not a setpoint. |
| `SET_TEMPERATURE` | unmapped |  |  | The station is not fixed. Use DRIVER_TEMP_SETTING or PASSENGER_TEMP_SETTING. |
| `SIGNAL_OFF` | action `SIGNAL_OFF` |  |  |  |
| `SPEED` | `Vehicle.Speed` | km/h |  |  |
| `STEERING_ANGLE` | `Vehicle.Chassis.SteeringWheel.Angle` | degrees |  |  |
| `STFT_B1` | `Vehicle.OBD.ShortTermFuelTrim1` | percent |  | COVESA OBD overlay, PID 06. |
| `STFT_B2` | `Vehicle.OBD.ShortTermFuelTrim2` | percent |  | COVESA OBD overlay, PID 08. |
| `SUPPORTED_PIDS_01_20` | query `SUPPORTED_PIDS_01_20` |  |  |  |
| `TIME_TO_FULL_CHARGE` | `Vehicle.Powertrain.TractionBattery.Charging.TimeToComplete` | s |  | Includes a scheduled delay before charging starts. |
| `TIMING_ADVANCE` | `Vehicle.OBD.TimingAdvance` | degrees |  | COVESA OBD overlay, PID 0E. The value is the angle, not the raw OBD byte. |
| `TPMS_FRONT_LEFT` | `Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure` | kPa |  | Front-axle left tire pressure. |
| `TPMS_FRONT_RIGHT` | `Vehicle.Chassis.Axle.Row1.Wheel.Right.Tire.Pressure` | kPa |  | Front-axle right tire pressure. |
| `TPMS_REAR_LEFT` | `Vehicle.Chassis.Axle.Row2.Wheel.Left.Tire.Pressure` | kPa |  | Rear-axle left tire pressure. |
| `TPMS_REAR_RIGHT` | `Vehicle.Chassis.Axle.Row2.Wheel.Right.Tire.Pressure` | kPa |  | Rear-axle right tire pressure. |
| `TPS` | `Vehicle.Powertrain.CombustionEngine.TPS` | percent |  |  |
| `TRUNK` | `Vehicle.Body.Trunk.Rear.IsOpen` |  | `true` | Rear luggage compartment. False is closed and true is open. The action opens the trunk. |
| `UNLOCK` | `Vehicle.Cabin.IsCentralLockEngaged` |  | `false` |  |
| `VIN` | `Vehicle.VehicleIdentification.VIN` |  |  |  |
| `WAKE_UP` | action `WAKE_UP` |  |  |  |
| `WINDOW_CHILD_LOCK` | `Vehicle.Cabin.IsWindowChildLockEngaged` |  | `true` | Disables the rear window switches so only the driver can operate them. |
| `WINDOW_CHILD_UNLOCK` | `Vehicle.Cabin.IsWindowChildLockEngaged` |  | `false` |  |
| `WIPERS` | `Vehicle.Body.Windshield.Front.Wiping.Mode` |  | `"MEDIUM"` | Front windshield. Use MEDIUM when the command does not select a speed. |

## Related pages

[VSS paths and semantics](vss.md) · [Migration](migration.md) · [Historical format 1 reference](format-1.md)
