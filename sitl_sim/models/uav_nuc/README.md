# UAV_NUC Gazebo Classic model

This is an independent PX4 v1.17 Gazebo Classic model derived from Iris.
It does not overwrite the original Iris model.

Measured inputs currently represented in the model:

- total mass: 2.305 kg
- simulated motor coordinates: 117.44 mm by 117.44 mm from the IMU origin
  (166.09 mm radial distance; deliberately different from the earlier
  84-by-84 mm measurement to provide the requested 20 mm prop-tip clearance)
- propeller: 51466R, three blades, nominal diameter 129.54 mm and nominal
  pitch 4.66 inches; each three-blade visual is made by extracting one blade
  from the original Iris two-blade mesh, copying it three times, and placing
  the copies at 0, 120 and 240 degrees
- centre of gravity: 30 mm below the IMU (current estimate)
- landing contact plane: 215 mm below the IMU
- combined body/battery collision height: 135 mm
- D435 sensor reference centre: 40 mm forward and 65 mm above the IMU

The inertia tensor and motor thrust constant remain engineering estimates and
must be replaced after pendulum/CAD inertia measurement and thrust-stand data.
The retained Iris blade surface is a visual approximation of the 51466R. The
4.66-inch pitch is not yet represented by a measured 51466R mesh or a
blade-element aerodynamic model.

On the simulation desktop, start the model with:

```bash
bash ~/UAV_NUC/sitl_sim/07_start_uav_nuc_preview.sh
```

Gazebo camera controls: right-drag to zoom, middle-drag to pan, and left-drag
to orbit. The PX4 user-camera plugin automatically tracks `uav_nuc`.
