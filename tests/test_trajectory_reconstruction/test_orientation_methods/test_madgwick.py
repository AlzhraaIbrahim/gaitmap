import pytest

from gaitmap.base import BaseType, BaseOrientationMethods
from gaitmap.trajectory_reconstruction import MadgwickAHRS
from tests.mixins.test_algorithm_mixin import TestAlgorithmMixin
from tests.test_trajectory_reconstruction.test_orientation_methods.test_ori_method_mixin import (
    TestOrientationMethodMixin,
)


class TestMetaFunctionality(TestAlgorithmMixin):
    algorithm_class = MadgwickAHRS
    __test__ = True

    @pytest.fixture()
    def after_action_instance(self, healthy_example_imu_data, healthy_example_stride_events) -> BaseType:
        position = MadgwickAHRS()
        position.estimate(
            healthy_example_imu_data["left_sensor"].iloc[:10], sampling_rate_hz=1,
        )
        return position


class TestSimpleRotations(TestOrientationMethodMixin):
    __test__ = True

    def init_algo_class(self) -> BaseOrientationMethods:
        return MadgwickAHRS()
