from importlib.resources import open_text

import pandas as pd
import pytest

from tests import example_data
from tests._regression_utils import PyTestSnapshotTest


def get_healthy_example_imu_data():
    """Example IMU data from a healthy subject doing a 2x20m gait test.

    The sampling rate is 204.8 Hz

    For expected results see:
        - :ref:`healthy_example_stride_borders`
    """
    with open_text(example_data, "imu_sample.csv") as test_data:
        data = pd.read_csv(test_data, header=[0, 1], index_col=0)

    # Get index in seconds
    data.index /= 204.8
    return data


healthy_example_imu_data = pytest.fixture()(get_healthy_example_imu_data)


def get_healthy_example_stride_borders():
    """Hand labeled stride borders for :ref:`healthy_example_imu_data`.

    The stride borders are hand labeled at the gyr_ml minima before the toe-off.
    """
    with open_text(example_data, "stride_borders_sample.csv") as test_data:
        data = pd.read_csv(test_data, header=0)

    # Convert to dict with sensor name as key.
    # Sensor name here is derived from the foot. In the real pipeline that would be provided to the algo.
    data["sensor"] = data["foot"] + "_sensor"
    data = data.set_index("sensor")
    data = data.groupby(level=0)
    data = {k: v.reset_index(drop=True) for k, v in data}

    return data


healthy_example_stride_borders = pytest.fixture()(get_healthy_example_stride_borders)


def get_healthy_example_mocap_data():
    """3D Mocap information of the foot synchronised with :ref:`healthy_example_imu_data`.

    The sampling rate is 100 Hz.

    The stride borders are hand labeled at the gyr_ml minima before the toe-off.
    """
    with open_text(example_data, "mocap_sample.csv") as test_data:
        data = pd.read_csv(test_data, header=[0, 1], index_col=0)

    # Get index in seconds
    data.index /= 100.0
    return data


healthy_example_mocap_data = pytest.fixture()(get_healthy_example_mocap_data)


def get_healthy_example_stride_events():
    """Gait events extracted based on mocap data.

    The gait events are extracted based on the mocap data. but are converted to fit the indices of
    `healthy_example_imu_data`.

    However, because the values are extracted from another system the `min_vel` might not fit perfectly onto the imu
    data.

    This fixture returns a dictionary of stridelists, where the key is the sensor name.
    """
    with open_text(example_data, "stride_events_sample.csv") as test_data:
        data = pd.read_csv(test_data, header=0)

    # Convert to dict with sensor name as key.
    # Sensor name here is derived from the foot. In the real pipeline that would be provided to the algo.
    data["sensor"] = data["foot"] + "_sensor"
    data = data.set_index("sensor")
    data = data.groupby(level=0)
    data = {k: v.reset_index(drop=True) for k, v in data}
    return data


healthy_example_stride_events = pytest.fixture()(get_healthy_example_stride_events)


def get_healthy_example_orientation():
    """Foot orientation calculated based on mocap data synchronised with :ref:`healthy_example_imu_data`.

    The sampling rate is 100 Hz.

    This data provides the orientation per stride in the default format.

    This fixture returns a dictionary, where the key is the sensor name.
    """
    with open_text(example_data, "orientation_sample.csv") as test_data:
        data = pd.read_csv(test_data, header=0, index_col=[0, 1, 2])

    # Convert to dict with sensor name as key.
    data = data.groupby(level=0)
    data = {k: v.reset_index(drop=True, level=0) for k, v in data}
    return data


healthy_example_orientation = pytest.fixture()(get_healthy_example_orientation)


def get_healthy_example_position():
    """Foot position calculated based on mocap data synchronised with :ref:`healthy_example_imu_data`.

    The sampling rate is 100 Hz.

    This data provides the position per stride in the default format.
    The position is equivalent to the position of the heel marker.

    This fixture returns a dictionary, where the key is the sensor name.
    """
    with open_text(example_data, "position_sample.csv") as test_data:
        data = pd.read_csv(test_data, header=0, index_col=[0, 1, 2])

    # Convert to dict with sensor name as key.
    data = data.groupby(level=0)
    data = {k: v.reset_index(drop=True, level=0) for k, v in data}
    return data


healthy_example_position = pytest.fixture()(get_healthy_example_position)


@pytest.fixture
def snapshot(request):
    with PyTestSnapshotTest(request) as snapshot_test:
        yield snapshot_test


def pytest_addoption(parser):
    group = parser.getgroup("snapshottest")
    group.addoption(
        "--snapshot-update", action="store_true", default=False, dest="snapshot_update", help="Update the snapshots."
    )
