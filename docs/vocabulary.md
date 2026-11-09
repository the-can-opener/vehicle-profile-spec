# Keyword vocabulary

[Overview](../README.md) · [Documentation index](README.md)

Generated from [vocabulary.yaml](vocabulary.yaml); do not edit this listing by hand.

| Keyword | Mapping | Unit | Write target | Notes |
|---|---|---|---|---|
| `ACCELERATOR_PEDAL` | `Vehicle.Chassis.Accelerator.PedalPosition` | percent |  | Accelerator pedal travel. 0 is not depressed and 100 is fully depressed. Throttle plate position is TPS. |
| `ACTUAL_TORQUE` | `Vehicle.Powertrain.CombustionEngine.Torque` | Nm |  | Current engine torque. |
| `AMBIENT_TEMP` | `Vehicle.Exterior.AirTemperature` | Celsius |  |  |
| `AUX_BATTERY_VOLTAGE` | `Vehicle.LowVoltageBattery.CurrentVoltage` | V |  | 12 V low-voltage battery. OBD control-module voltage is MODULE_VOLTAGE. |
| `BARO` | `Vehicle.OBD.BarometricPressure` | kPa |  | COVESA OBD overlay, PID 33. |
| `BOOST_PRESSURE` | unmapped |  |  | Derived as MAP minus BARO; VSS has no separate boost-pressure signal. |
| `BRAKE_LIGHTS` | `Vehicle.Body.Lights.Brake.IsActive` |  |  |  |
| `BRAKE_PEDAL` | `Vehicle.Chassis.Brake.PedalPosition` | percent |  | Brake pedal travel. 0 is not depressed and 100 is fully depressed. Brake lamps are BRAKE_LIGHTS. |
| `CABIN_TEMP` | `Vehicle.Cabin.HVAC.AmbientAirTemperature` | Celsius |  |  |
| `CABIN_TEMP_SETPOINT` | unmapped |  |  | The station is not fixed. Use DRIVER_TEMP_SETTING or PASSENGER_TEMP_SETTING. |
| `CHARGER` | `Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.AnyPosition.IsChargingCableConnected` |  |  | Single charging port. Use a position instance instead of AnyPosition when the port location is known. |
| `CHARGER_TYPE` | unmapped |  |  | Active connected charger type (none, ac, dc) has no single VSS signal; SupportedInletTypes is an attribute array. |
| `CHARGE_LIMIT` | `Vehicle.Powertrain.TractionBattery.Charging.ChargeLimit` | percent |  |  |
| `CHARGE_PORT` | `Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.AnyPosition.IsFlapOpen` |  | `true` | Single charging port. Use a position instance instead of AnyPosition when the port location is known. |
| `CHARGE_POWER` | `Vehicle.Powertrain.TractionBattery.Charging.AveragePower` | kW |  | Average power of the current or last charging event. |
| `CHARGE_RATE` | `Vehicle.Powertrain.TractionBattery.Charging.ChargeRate` | km/h |  |  |
| `CHARGE_TIME_REMAINING` | `Vehicle.Powertrain.TractionBattery.Charging.TimeToComplete` | s |  | Includes a scheduled delay before charging starts. |
| `CHARGING` | `Vehicle.Powertrain.TractionBattery.Charging.IsCharging` |  |  | Active charging status. Start/stop commands map to Vehicle.Powertrain.TractionBattery.Charging.StartStopCharging. |
| `CLEAR_DTC` | action `CLEAR_DTC` |  |  |  |
| `CLIMATE` | unmapped |  |  | No single climate power actuator. Air conditioning is Vehicle.Cabin.HVAC.IsAirConditioningActive. |
| `CLUTCH_PEDAL` | `Vehicle.Chassis.Clutch.PedalPosition` | percent |  | Clutch pedal travel. 0 is not depressed and 100 is fully depressed. Clutch engagement is Vehicle.Powertrain.Transmission.ClutchEngagement. |
| `CRUISE_CONTROL` | `Vehicle.ADAS.CruiseControl.IsActive` |  |  | Cruise control engaged. Master switch is Vehicle.ADAS.CruiseControl.IsEnabled. |
| `DIST_SINCE_CLEAR` | `Vehicle.OBD.DistanceSinceDTCClear` | km |  | COVESA OBD overlay, PID 31. |
| `DOORS` | `Vehicle.Cabin.IsCentralLockEngaged` |  |  | Central locking for all doors. |
| `DRIVER_TEMP_SETTING` | `Vehicle.Cabin.HVAC.Station.Row1.Driver.Temperature` | Celsius |  |  |
| `DRIVER_TORQUE_DEMAND` | unmapped |  |  | OBD driver-demand engine torque (PID 61) is not in the VSS 6.1 catalog or the OBD overlay. |
| `ECT` | `Vehicle.Powertrain.CombustionEngine.EngineCoolant.Temperature` | Celsius |  |  |
| `ECU_WAKE` | action `ECU_WAKE` |  |  |  |
| `ENGINE` | `Vehicle.Powertrain.CombustionEngine.IsRunning` |  |  | Engine rotating. Remote start is action REMOTE_START. |
| `ENGINE_LOAD` | `Vehicle.OBD.EngineLoad` | percent |  | COVESA OBD overlay, PID 04. |
| `FLASH_LIGHTS` | action `FLASH_LIGHTS` |  |  |  |
| `FOG_LIGHTS` | `Vehicle.Body.Lights.Fog.Front.IsOn` |  | `true` | Front fog lights. Rear fog lights are Vehicle.Body.Lights.Fog.Rear.IsOn. |
| `FRONT_DEFROST` | `Vehicle.Cabin.HVAC.IsFrontDefrosterActive` |  | `true` | Front defroster. Rear defroster is REAR_DEFROST. |
| `FRONT_LEFT_DOOR` | `Vehicle.Cabin.Door.Row1.DriverSide.IsOpen` |  |  | Closed and open. Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `FRONT_LEFT_SEATBELT` | `Vehicle.Cabin.Seat.Row1.DriverSide.IsBelted` |  |  | Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `FRONT_LEFT_SEAT_HEATER` | unmapped |  |  | Vehicle.Cabin.Seat.Row1.DriverSide.HeatingCooling is a signed percent (-100 to 100), not discrete off/low/medium/high levels. |
| `FRONT_LEFT_TIRE_PRESSURE` | `Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure` | kPa |  | Front-axle left tire pressure. |
| `FRONT_LEFT_WINDOW` | `Vehicle.Cabin.Door.Row1.DriverSide.Window.IsOpen` |  |  | Closed and open. Left/right mapping assumes left-hand-drive; review vehicle applicability. Travel in percent is FRONT_LEFT_WINDOW_POSITION. |
| `FRONT_LEFT_WINDOW_POSITION` | `Vehicle.Cabin.Door.Row1.DriverSide.Window.Position` | percent |  | Left/right mapping assumes left-hand-drive; review vehicle applicability. 0 is fully closed and 100 is fully open. |
| `FRONT_RIGHT_DOOR` | `Vehicle.Cabin.Door.Row1.PassengerSide.IsOpen` |  |  | Closed and open. Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `FRONT_RIGHT_SEATBELT` | `Vehicle.Cabin.Seat.Row1.PassengerSide.IsBelted` |  |  | Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `FRONT_RIGHT_SEAT_HEATER` | unmapped |  |  | Vehicle.Cabin.Seat.Row1.PassengerSide.HeatingCooling is a signed percent (-100 to 100), not discrete off/low/medium/high levels. |
| `FRONT_RIGHT_TIRE_PRESSURE` | `Vehicle.Chassis.Axle.Row1.Wheel.Right.Tire.Pressure` | kPa |  | Front-axle right tire pressure. |
| `FRONT_RIGHT_WINDOW` | `Vehicle.Cabin.Door.Row1.PassengerSide.Window.IsOpen` |  |  | Closed and open. Left/right mapping assumes left-hand-drive; review vehicle applicability. Travel in percent is FRONT_RIGHT_WINDOW_POSITION. |
| `FRONT_RIGHT_WINDOW_POSITION` | `Vehicle.Cabin.Door.Row1.PassengerSide.Window.Position` | percent |  | Left/right mapping assumes left-hand-drive; review vehicle applicability. 0 is fully closed and 100 is fully open. |
| `FUEL_DOOR` | `Vehicle.Powertrain.FuelSystem.IsFuelPortFlapOpen` |  | `true` |  |
| `FUEL_LEVEL` | `Vehicle.Powertrain.FuelSystem.RelativeLevel` | percent |  |  |
| `FUEL_PRESSURE` | `Vehicle.OBD.FuelPressure` | kPa |  | COVESA OBD overlay, PID 0A. |
| `FUEL_RATE` | `Vehicle.OBD.FuelRate` | l/h |  | Engine fuel rate. COVESA OBD overlay, PID 5E. FuelSystem.InstantConsumption is l/100km. |
| `GEAR` | `Vehicle.Powertrain.Transmission.SelectedGear` |  |  | Selected gear. 126 = park, -1 = reverse, 0 = neutral, 127 = drive. |
| `HAZARDS` | `Vehicle.Body.Lights.Hazard.IsSignaling` |  | `true` |  |
| `HIGH_BEAMS` | `Vehicle.Body.Lights.Beam.High.IsOn` |  | `true` |  |
| `HOOD` | `Vehicle.Body.Hood.IsOpen` |  |  | Engine cover. Front luggage compartment is Vehicle.Body.Trunk.Front.IsOpen. |
| `HORN` | `Vehicle.Body.Horn.IsActive` |  | `true` |  |
| `HV_BATTERY_CAPACITY` | `Vehicle.Powertrain.TractionBattery.NetCapacity` | kWh |  | Net usable capacity. Gross capacity is Vehicle.Powertrain.TractionBattery.GrossCapacity. |
| `HV_BATTERY_CURRENT` | `Vehicle.Powertrain.TractionBattery.CurrentCurrent` | A |  |  |
| `HV_BATTERY_POWER` | unmapped |  |  | Vehicle.Powertrain.TractionBattery.CurrentPower is in W, while HV_BATTERY_POWER is in kW. |
| `HV_BATTERY_SOC` | `Vehicle.Powertrain.TractionBattery.StateOfCharge.Displayed` | percent |  | Customer-displayed state of charge. Physical state of charge is StateOfCharge.Current. |
| `HV_BATTERY_SOH` | `Vehicle.Powertrain.TractionBattery.StateOfHealth` | percent |  |  |
| `HV_BATTERY_TEMP` | `Vehicle.Powertrain.TractionBattery.Temperature.Average` | Celsius |  |  |
| `HV_BATTERY_VOLTAGE` | `Vehicle.Powertrain.TractionBattery.CurrentVoltage` | V |  |  |
| `IAT` | `Vehicle.OBD.IntakeTemp` | Celsius |  | COVESA OBD overlay, PID 0F. |
| `IGNITION` | `Vehicle.LowVoltageSystemState` |  |  | Power mode. Allowed values are UNDEFINED, LOCK, OFF, ACC, ON, and START. |
| `INTERIOR_LIGHTS` | `Vehicle.Cabin.Light.IsDomeOn` |  | `true` |  |
| `LAMBDA` | `Vehicle.OBD.O2WR.Sensor1.Lambda` |  |  | First wideband oxygen sensor, PID 24. Sensors 2 through 8 are Vehicle.OBD.O2WR.Sensor2.Lambda through Sensor8.Lambda. |
| `LEFT_SIGNAL` | `Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling` |  | `true` |  |
| `LOW_BEAMS` | `Vehicle.Body.Lights.Beam.Low.IsOn` |  | `true` |  |
| `LTFT_B1` | `Vehicle.OBD.LongTermFuelTrim1` | percent |  | COVESA OBD overlay, PID 07. |
| `LTFT_B2` | `Vehicle.OBD.LongTermFuelTrim2` | percent |  | COVESA OBD overlay, PID 09. |
| `MAF` | `Vehicle.Powertrain.CombustionEngine.MAF` | g/s |  |  |
| `MAP` | `Vehicle.Powertrain.CombustionEngine.MAP` | kPa |  |  |
| `MIL_STATUS` | `Vehicle.OBD.Status.IsMILOn` |  |  | Malfunction indicator lamp. COVESA OBD overlay, PID 01. |
| `MIRRORS` | unmapped |  |  | VSS separates side mirrors into Vehicle.Body.Mirrors.DriverSide.IsFolded and PassengerSide.IsFolded. |
| `MODULE_VOLTAGE` | `Vehicle.OBD.ControlModuleVoltage` | V |  | COVESA OBD overlay, PID 42. |
| `O2_DATA` | `Vehicle.OBD.O2.Sensor1.Voltage` | V |  | First narrowband sensor voltage, PID 14 byte A. Short-term trim is Vehicle.OBD.O2.Sensor1.ShortTermFuelTrim. Sensors 2 through 8 follow the same shape. |
| `ODOMETER` | `Vehicle.TraveledDistance` | m |  | Lifetime distance. |
| `OIL_LIFE` | unmapped |  |  | Vehicle.Powertrain.CombustionEngine.EngineOil.LifeRemaining is in seconds, not percent. |
| `OIL_PRESSURE` | unmapped |  |  | VSS has EngineOil.PressureStatus (string), not a numeric kPa oil-pressure signal. |
| `OIL_TEMP` | `Vehicle.Powertrain.CombustionEngine.EngineOil.Temperature` | Celsius |  |  |
| `PANIC` | action `PANIC` |  |  |  |
| `PARKING_BRAKE` | `Vehicle.Chassis.ParkingBrake.IsEngaged` |  | `true` |  |
| `PASSENGER_TEMP_SETTING` | `Vehicle.Cabin.HVAC.Station.Row1.Passenger.Temperature` | Celsius |  |  |
| `RANGE` | `Vehicle.Powertrain.Range` | m |  | Remaining range from all energy sources. |
| `READINESS_STATUS` | unmapped |  |  | OBD readiness monitors are a bitmap in PID 01 and are not a single signal. MIL state is Vehicle.OBD.Status.IsMILOn. |
| `READY` | unmapped |  |  | VSS has no propulsion-ready state signal; Vehicle.IsMoving only indicates motion. |
| `REAR_DEFROST` | `Vehicle.Cabin.HVAC.IsRearDefrosterActive` |  | `true` | Rear defroster. Front defroster is FRONT_DEFROST. |
| `REAR_LEFT_DOOR` | `Vehicle.Cabin.Door.Row2.DriverSide.IsOpen` |  |  | Closed and open. Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `REAR_LEFT_TIRE_PRESSURE` | `Vehicle.Chassis.Axle.Row2.Wheel.Left.Tire.Pressure` | kPa |  | Rear-axle left tire pressure. |
| `REAR_LEFT_WINDOW` | `Vehicle.Cabin.Door.Row2.DriverSide.Window.IsOpen` |  |  | Closed and open. Left/right mapping assumes left-hand-drive; review vehicle applicability. Travel in percent is REAR_LEFT_WINDOW_POSITION. |
| `REAR_LEFT_WINDOW_POSITION` | `Vehicle.Cabin.Door.Row2.DriverSide.Window.Position` | percent |  | Left/right mapping assumes left-hand-drive; review vehicle applicability. 0 is fully closed and 100 is fully open. |
| `REAR_RIGHT_DOOR` | `Vehicle.Cabin.Door.Row2.PassengerSide.IsOpen` |  |  | Closed and open. Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `REAR_RIGHT_TIRE_PRESSURE` | `Vehicle.Chassis.Axle.Row2.Wheel.Right.Tire.Pressure` | kPa |  | Rear-axle right tire pressure. |
| `REAR_RIGHT_WINDOW` | `Vehicle.Cabin.Door.Row2.PassengerSide.Window.IsOpen` |  |  | Closed and open. Left/right mapping assumes left-hand-drive; review vehicle applicability. Travel in percent is REAR_RIGHT_WINDOW_POSITION. |
| `REAR_RIGHT_WINDOW_POSITION` | `Vehicle.Cabin.Door.Row2.PassengerSide.Window.Position` | percent |  | Left/right mapping assumes left-hand-drive; review vehicle applicability. 0 is fully closed and 100 is fully open. |
| `REAR_WIPER` | `Vehicle.Body.Windshield.Rear.Wiping.Mode` |  | `"MEDIUM"` | Rear windshield. Use MEDIUM when the command does not select a speed. |
| `REVERSE_LIGHTS` | `Vehicle.Body.Lights.Backup.IsOn` |  |  |  |
| `RIGHT_SIGNAL` | `Vehicle.Body.Lights.DirectionIndicator.Right.IsSignaling` |  | `true` |  |
| `RPM` | `Vehicle.Powertrain.CombustionEngine.Speed` | rpm |  |  |
| `RUNNING_LIGHTS` | `Vehicle.Body.Lights.Running.IsOn` |  | `true` |  |
| `RUNTIME` | `Vehicle.OBD.RunTime` | s |  | Engine run time. COVESA OBD overlay, PID 1F. |
| `SEATBELT_WARNING` | `Vehicle.Cabin.IsSeatBeltWarningActive` |  |  | Vehicle seatbelt warning indicator. True means the indicator is active. Per-seat buckle state remains IsBelted. |
| `SPEED` | `Vehicle.Speed` | km/h |  |  |
| `STEERING_ANGLE` | `Vehicle.Chassis.SteeringWheel.Angle` | degrees |  |  |
| `STFT_B1` | `Vehicle.OBD.ShortTermFuelTrim1` | percent |  | COVESA OBD overlay, PID 06. |
| `STFT_B2` | `Vehicle.OBD.ShortTermFuelTrim2` | percent |  | COVESA OBD overlay, PID 08. |
| `SUNROOF` | `Vehicle.Cabin.Sunroof.Switch` |  | `"OPEN"` | Switch command/state. Travel in percent is SUNROOF_POSITION. |
| `SUNROOF_POSITION` | `Vehicle.Cabin.Sunroof.Position` | percent |  | 0 is fully closed, 100 is fully opened, and -100 is fully tilted. |
| `SUPPORTED_PIDS_01_20` | query `SUPPORTED_PIDS_01_20` |  |  |  |
| `TIMING_ADVANCE` | `Vehicle.OBD.TimingAdvance` | degrees |  | COVESA OBD overlay, PID 0E. The value is the angle, not the raw OBD byte. |
| `TPS` | `Vehicle.Powertrain.CombustionEngine.TPS` | percent |  |  |
| `TRANSMISSION_TEMP` | `Vehicle.Powertrain.Transmission.Temperature` | Celsius |  |  |
| `TRUNK` | `Vehicle.Body.Trunk.Rear.IsOpen` |  | `true` | Rear luggage compartment. False is closed and true is open. The action opens the trunk. |
| `VIN` | `Vehicle.VehicleIdentification.VIN` |  |  |  |
| `WASHER` | action `WASHER` |  |  |  |
| `WINDOW_CHILD_LOCK` | `Vehicle.Cabin.IsWindowChildLockEngaged` |  | `true` | Disables the rear window switches so only the driver can operate them. |
| `WIPERS` | `Vehicle.Body.Windshield.Front.Wiping.Mode` |  | `"MEDIUM"` | Front windshield. Use MEDIUM when the command does not select a speed. |

## Legacy keywords

Format 1 predicate, past-tense, and verb-specific keyword variants retained for migration compatibility.

| Keyword | Mapping | Unit | Write target | Notes |
|---|---|---|---|---|
| `ACTUATE_TRUNK_FRONT` | action `ACTUATE_TRUNK_FRONT` |  |  |  |
| `ACTUATE_TRUNK_REAR` | action `ACTUATE_TRUNK_REAR` |  |  |  |
| `ADD_CHARGE_SCHEDULE` | action `ADD_CHARGE_SCHEDULE` |  |  |  |
| `ADD_PRECONDITION_SCHEDULE` | action `ADD_PRECONDITION_SCHEDULE` |  |  |  |
| `AUTO_CONDITIONING_START` | action `AUTO_CONDITIONING_START` |  |  |  |
| `AUTO_CONDITIONING_STOP` | action `AUTO_CONDITIONING_STOP` |  |  |  |
| `BATTERY_LEVEL` | `Vehicle.Powertrain.TractionBattery.StateOfCharge.Displayed` | percent |  | Customer-displayed state of charge. Physical state of charge is StateOfCharge.Current. |
| `BATTERY_RANGE` | `Vehicle.Powertrain.TractionBattery.Range` | m |  | Battery-only remaining range. |
| `CANCEL_SOFTWARE_UPDATE` | action `CANCEL_SOFTWARE_UPDATE` |  |  |  |
| `CHARGER_CURRENT` | `Vehicle.Powertrain.TractionBattery.Charging.ChargeCurrent.DC` | A |  | DC inlet current. AC current is Phase1, Phase2, and Phase3. |
| `CHARGER_POWER` | `Vehicle.Powertrain.TractionBattery.Charging.AveragePower` | kW |  | Average power of the current or last charging event. |
| `CHARGER_VOLTAGE` | `Vehicle.Powertrain.TractionBattery.Charging.ChargeVoltage.DC` | V |  | DC inlet voltage. AC voltage is Phase1, Phase2, and Phase3. |
| `CHARGE_ENERGY_ADDED` | unmapped |  |  | Session energy added has no VSS signal. Vehicle.Powertrain.TractionBattery.AccumulatedChargedEnergy is lifetime charged energy. |
| `CHARGE_LIMIT_SOC` | `Vehicle.Powertrain.TractionBattery.Charging.ChargeLimit` | percent |  |  |
| `CHARGE_PORT_CLOSE` | `Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.AnyPosition.IsFlapOpen` |  | `false` | Single charging port. Use a position instance instead of AnyPosition when the port location is known. |
| `CHARGE_PORT_OPEN` | `Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.AnyPosition.IsFlapOpen` |  | `true` | Single charging port. Use a position instance instead of AnyPosition when the port location is known. |
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
| `ESTIMATED_RANGE` | `Vehicle.Powertrain.Range` | m |  | Remaining range from all energy sources. |
| `FRONT_LEFT_DOOR_OPEN` | `Vehicle.Cabin.Door.Row1.DriverSide.IsOpen` |  | `true` | Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `FRONT_RIGHT_DOOR_OPEN` | `Vehicle.Cabin.Door.Row1.PassengerSide.IsOpen` |  | `true` | Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `HAZARD_LIGHTS` | `Vehicle.Body.Lights.Hazard.IsSignaling` |  | `true` |  |
| `HIGH_BEAM` | `Vehicle.Body.Lights.Beam.High.IsOn` |  | `true` |  |
| `IDEAL_RANGE` | unmapped |  |  | VSS has no ideal or rated range separate from remaining range. |
| `LOCK` | `Vehicle.Cabin.IsCentralLockEngaged` |  | `true` |  |
| `LOCKED` | `Vehicle.Cabin.IsCentralLockEngaged` |  |  |  |
| `LOW_BEAM` | `Vehicle.Body.Lights.Beam.Low.IsOn` |  | `true` |  |
| `OPEN_FRONT_LEFT_WINDOW` | `Vehicle.Cabin.Door.Row1.DriverSide.Window.Position` | percent | `100` | Left/right mapping assumes left-hand-drive; review vehicle applicability. 100 is fully open when the command does not select a percent. |
| `OPEN_FRONT_RIGHT_WINDOW` | `Vehicle.Cabin.Door.Row1.PassengerSide.Window.Position` | percent | `100` | Left/right mapping assumes left-hand-drive; review vehicle applicability. 100 is fully open when the command does not select a percent. |
| `OPEN_FRUNK` | `Vehicle.Body.Trunk.Front.IsOpen` |  | `true` | Front luggage compartment. Vehicle.Body.Hood is the engine cover. |
| `OPEN_REAR_LEFT_WINDOW` | `Vehicle.Cabin.Door.Row2.DriverSide.Window.Position` | percent | `100` | Left/right mapping assumes left-hand-drive; review vehicle applicability. 100 is fully open when the command does not select a percent. |
| `OPEN_REAR_RIGHT_WINDOW` | `Vehicle.Cabin.Door.Row2.PassengerSide.Window.Position` | percent | `100` | Left/right mapping assumes left-hand-drive; review vehicle applicability. 100 is fully open when the command does not select a percent. |
| `OPEN_TRUNK` | `Vehicle.Body.Trunk.Rear.IsOpen` |  | `true` |  |
| `OUTSIDE_TEMP` | `Vehicle.Exterior.AirTemperature` | Celsius |  |  |
| `PLUGGED_IN` | `Vehicle.Powertrain.TractionBattery.Charging.ChargingPort.AnyPosition.IsChargingCableConnected` |  |  | Single charging port. Use a position instance instead of AnyPosition when the port location is known. |
| `REAR_LEFT_DOOR_OPEN` | `Vehicle.Cabin.Door.Row2.DriverSide.IsOpen` |  | `true` | Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `REAR_RIGHT_DOOR_OPEN` | `Vehicle.Cabin.Door.Row2.PassengerSide.IsOpen` |  | `true` | Left/right mapping assumes left-hand-drive; review vehicle applicability. |
| `REAR_WIPER_OFF` | `Vehicle.Body.Windshield.Rear.Wiping.Mode` |  | `"OFF"` | Rear windshield. |
| `REMOTE_START` | action `REMOTE_START` |  |  |  |
| `REMOVE_CHARGE_SCHEDULE` | action `REMOVE_CHARGE_SCHEDULE` |  |  |  |
| `REMOVE_PRECONDITION_SCHEDULE` | action `REMOVE_PRECONDITION_SCHEDULE` |  |  |  |
| `SCHEDULE_SOFTWARE_UPDATE` | action `SCHEDULE_SOFTWARE_UPDATE` |  |  |  |
| `SET_CHARGE_LIMIT` | unmapped |  |  | The limit is a caller-supplied value, not a fixed write target. The signal is Vehicle.Powertrain.TractionBattery.Charging.ChargeLimit. |
| `SET_CHARGING_AMPS` | unmapped |  |  | No commanded charging-current actuator. MaximumChargingCurrent is inlet capability, not a setpoint. |
| `SET_TEMPERATURE` | unmapped |  |  | The station is not fixed. Use DRIVER_TEMP_SETTING or PASSENGER_TEMP_SETTING. |
| `SIGNAL_OFF` | action `SIGNAL_OFF` |  |  |  |
| `TIME_TO_FULL_CHARGE` | `Vehicle.Powertrain.TractionBattery.Charging.TimeToComplete` | s |  | Includes a scheduled delay before charging starts. |
| `TPMS_FRONT_LEFT` | `Vehicle.Chassis.Axle.Row1.Wheel.Left.Tire.Pressure` | kPa |  | Front-axle left tire pressure. |
| `TPMS_FRONT_RIGHT` | `Vehicle.Chassis.Axle.Row1.Wheel.Right.Tire.Pressure` | kPa |  | Front-axle right tire pressure. |
| `TPMS_REAR_LEFT` | `Vehicle.Chassis.Axle.Row2.Wheel.Left.Tire.Pressure` | kPa |  | Rear-axle left tire pressure. |
| `TPMS_REAR_RIGHT` | `Vehicle.Chassis.Axle.Row2.Wheel.Right.Tire.Pressure` | kPa |  | Rear-axle right tire pressure. |
| `UNLOCK` | `Vehicle.Cabin.IsCentralLockEngaged` |  | `false` |  |
| `WAKE_UP` | action `WAKE_UP` |  |  |  |
| `WINDOW_CHILD_UNLOCK` | `Vehicle.Cabin.IsWindowChildLockEngaged` |  | `false` |  |

## Related pages

[VSS paths and semantics](vss.md) · [Migration](migration.md) · [Historical format 1 reference](format-1.md)
