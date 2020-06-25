"""Test the dataset helpers."""
from typing import List, Callable
import numpy as np
import pandas as pd

import pytest
from pandas._testing import assert_frame_equal

from gaitmap.utils.consts import SF_COLS, SF_GYR, SF_ACC, BF_COLS, BF_GYR, BF_ACC
from gaitmap.utils.dataset_helper import (
    _has_sf_cols,
    _has_bf_cols,
    is_single_sensor_dataset,
    is_multi_sensor_dataset,
    get_multi_sensor_dataset_names,
    is_single_sensor_stride_list,
    is_multi_sensor_stride_list,
    set_correct_index,
    is_single_sensor_position_list,
    is_single_sensor_orientation_list,
    is_multi_sensor_position_list,
    is_multi_sensor_orientation_list,
    is_single_sensor_regions_of_interest_list,
    is_multi_sensor_regions_of_interest_list,
)


def _create_test_multiindex():
    return pd.MultiIndex.from_product([list("abc"), list("123")])


@pytest.fixture(params=(("both", True, True), ("acc", True, False), ("gyr", False, True)))
def combinations(request):
    return request.param


@pytest.fixture(params=("any", "body", "sensor"))
def frame(request):
    return request.param


@pytest.fixture(params=("any", "min_vel", "ic", "segmented"))
def stride_types(request):
    return request.param


@pytest.fixture(params=("any", "gs", "roi"))
def roi_types(request):
    return request.param


@pytest.fixture(params=(True, False))
def as_index(request):
    return request.param


class TestColumnHelper:

    method: Callable
    cols: List[str]
    gyr_cols: List[str]
    acc_cols: List[str]

    @pytest.fixture(params=["sf", "bf"], autouse=True)
    def select_method(self, request):
        self.method = {"sf": _has_sf_cols, "bf": _has_bf_cols}[request.param]
        self.cols = {"sf": SF_COLS, "bf": BF_COLS}[request.param]
        self.gyr_cols = {"sf": SF_GYR, "bf": BF_GYR}[request.param]
        self.acc_cols = {"sf": SF_ACC, "bf": BF_ACC}[request.param]

    def test_columns_correct(self):
        assert self.method(self.cols)

    def test_gyr_columns_only(self):
        assert self.method(self.gyr_cols, check_acc=False)

    def test_acc_columns_only(self):
        assert self.method(self.acc_cols, check_gyr=False)

    def test_missing_columns(self):
        assert not self.method(self.acc_cols)

    def test_wrong_names(self):
        assert not self.method(list(range(6)))

    def test_missing_acc_columns(self):
        assert not self.method(self.acc_cols[:-1], check_gyr=False)

    def test_missing_gyr_columns(self):
        assert not self.method(self.gyr_cols[:-1], check_acc=False)


class TestIsSingleSensorDataset:
    @pytest.mark.parametrize(
        "value",
        ({"test": pd.DataFrame}, list(range(6)), "test", np.arange(6), pd.DataFrame(columns=_create_test_multiindex())),
    )
    def test_wrong_datatype(self, value):
        assert not is_single_sensor_dataset(value, check_acc=False, check_gyr=False)

    def test_correct_datatype(self):
        assert is_single_sensor_dataset(pd.DataFrame(), check_acc=False, check_gyr=False)

    @pytest.mark.parametrize(
        "cols, frame_valid, col_check_valid",
        (
            (SF_COLS, "sensor", "both"),
            (BF_COLS, "body", "both"),
            (BF_GYR, "body", "gyr"),
            (BF_ACC, "body", "acc"),
            (SF_GYR, "sensor", "gyr"),
            (SF_ACC, "sensor", "acc"),
        ),
    )
    def test_correct_columns(self, cols, frame_valid, col_check_valid, combinations, frame):
        """Test all possible combinations of inputs."""
        col_check, check_acc, check_gyro = combinations
        output = is_single_sensor_dataset(
            pd.DataFrame(columns=cols), check_acc=check_acc, check_gyr=check_gyro, frame=frame
        )

        valid_frame = (frame_valid == frame) or (frame == "any")
        valid_cols = (col_check == col_check_valid) or (col_check_valid == "both")
        expected_outcome = valid_cols and valid_frame

        assert output == expected_outcome

    def test_invalid_frame_argument(self):
        with pytest.raises(ValueError):
            is_single_sensor_dataset(pd.DataFrame(), frame="invalid_value")


class TestIsMultiSensorDataset:
    @pytest.mark.parametrize(
        "value", (list(range(6)), "test", np.arange(6), {}, pd.DataFrame(), pd.DataFrame(columns=[*range(3)])),
    )
    def test_wrong_datatype(self, value):
        assert not is_multi_sensor_dataset(value, check_acc=False, check_gyr=False)

    def test_correct_datatype(self):
        assert is_multi_sensor_dataset(
            pd.DataFrame([[*range(9)]], columns=_create_test_multiindex()), check_acc=False, check_gyr=False
        )

    @pytest.mark.parametrize(
        "cols, frame_valid, col_check_valid",
        (
            (SF_COLS, "sensor", "both"),
            (BF_COLS, "body", "both"),
            (BF_GYR, "body", "gyr"),
            (BF_ACC, "body", "acc"),
            (SF_GYR, "sensor", "gyr"),
            (SF_ACC, "sensor", "acc"),
        ),
    )
    def test_correct_columns(self, cols, frame_valid, col_check_valid, combinations, frame):
        """Test all possible combinations of inputs."""
        col_check, check_acc, check_gyro = combinations
        output = is_multi_sensor_dataset(
            pd.DataFrame([[*range(len(cols) * 2)]], columns=pd.MultiIndex.from_product((("a", "b"), cols))),
            check_acc=check_acc,
            check_gyr=check_gyro,
            frame=frame,
        )

        valid_frame = (frame_valid == frame) or (frame == "any")
        valid_cols = (col_check == col_check_valid) or (col_check_valid == "both")
        expected_outcome = valid_cols and valid_frame

        assert output == expected_outcome

    def test_invalid_frame_argument(self):
        with pytest.raises(ValueError):
            is_multi_sensor_dataset(
                pd.DataFrame([[*range(9)]], columns=_create_test_multiindex()), frame="invalid_value"
            )


class TestGetMultiSensorDatasetNames:
    @pytest.mark.parametrize("obj", ({"a": [], "b": [], "c": []}, pd.DataFrame(columns=_create_test_multiindex())))
    def test_names_simple(self, obj):
        assert set(get_multi_sensor_dataset_names(obj)) == {"a", "b", "c"}


class TestIsSingleSensorStrideList:
    @pytest.mark.parametrize(
        "value",
        (
            list(range(6)),
            "test",
            np.arange(6),
            {},
            pd.DataFrame(),
            pd.DataFrame(columns=[*range(3)]),
            pd.DataFrame([[*range(9)]], columns=_create_test_multiindex()),
        ),
    )
    def test_wrong_datatype(self, value):
        assert not is_single_sensor_stride_list(value)

    @pytest.mark.parametrize(
        "cols, stride_types_valid",
        (
            (["s_id", "start", "end", "gsd_id"], ["any"]),
            (["s_id", "start", "end", "gsd_id", "something_extra"], ["any"]),
            (["s_id", "start", "end", "gsd_id", "pre_ic", "ic", "min_vel", "tc"], ["segmented", "min_vel", "ic"]),
            (
                ["s_id", "start", "end", "gsd_id", "pre_ic", "ic", "min_vel", "tc", "something_extra"],
                ["segmented", "min_vel", "ic"],
            ),
            (["s_id", "start", "end", "gsd_id", "ic", "min_vel", "tc"], ["ic", "segmented"]),
            (["s_id", "start", "end", "gsd_id", "ic", "min_vel", "tc", "something_extra"], ["ic", "segmented"]),
        ),
    )
    def test_valid_versions(self, cols, stride_types_valid, stride_types, as_index):
        expected_outcome = stride_types in stride_types_valid or stride_types == "any"
        df = pd.DataFrame(columns=cols)
        if as_index:
            df = df.set_index("s_id")

        out = is_single_sensor_stride_list(df, stride_type=stride_types)

        assert expected_outcome == out

    @pytest.mark.parametrize(
        "start, min_vel, expected",
        ((np.arange(10), np.arange(10), True), (np.arange(10), np.arange(10) + 1, False), ([], [], True)),
    )
    def test_columns_same_min_vel(self, start, min_vel, expected):
        """Test that the column equals check for min_vel_strides work."""
        min_vel_cols = ["s_id", "start", "end", "gsd_id", "pre_ic", "ic", "min_vel", "tc"]
        stride_list = pd.DataFrame(columns=min_vel_cols)
        stride_list["s_id"] = start
        stride_list["start"] = start
        stride_list["min_vel"] = min_vel

        out = is_single_sensor_stride_list(stride_list, stride_type="min_vel")

        assert out == expected

    @pytest.mark.parametrize(
        "start, ic, expected",
        ((np.arange(10), np.arange(10), True), (np.arange(10), np.arange(10) + 1, False), ([], [], True)),
    )
    def test_columns_same_ic(self, start, ic, expected):
        """Test that the column equals check for ic_strides work."""
        min_vel_cols = ["s_id", "start", "end", "gsd_id", "ic", "min_vel", "tc"]
        stride_list = pd.DataFrame(columns=min_vel_cols)
        stride_list["s_id"] = start
        stride_list["start"] = start
        stride_list["ic"] = ic

        out = is_single_sensor_stride_list(stride_list, stride_type="ic")

        assert out == expected

    def test_invalid_stride_type_argument(self):
        valid_cols = ["s_id", "start", "end", "gsd_id"]
        valid = pd.DataFrame(columns=valid_cols)

        with pytest.raises(ValueError):
            is_single_sensor_stride_list(valid, stride_type="invalid_value")

    def test_identical_stride_ids(self):
        """Test that the search for identical stride ids works."""
        min_vel_cols = ["s_id", "start", "end"]
        stride_list = pd.DataFrame(columns=min_vel_cols)
        stride_list["s_id"] = np.array([1, 2, 2])
        expected_outcome = False

        out = is_single_sensor_stride_list(stride_list, stride_type="min_vel")

        assert expected_outcome == out


class TestIsMultiSensorStrideList:
    @pytest.mark.parametrize(
        "value", (list(range(6)), "test", np.arange(6), {}, pd.DataFrame(), pd.DataFrame(columns=[*range(3)])),
    )
    def test_wrong_datatype(self, value):
        assert not is_multi_sensor_stride_list(value)

    @pytest.mark.parametrize(
        "cols, stride_types_valid",
        (
            (["s_id", "start", "end", "gsd_id"], ["any"]),
            (["s_id", "start", "end", "gsd_id", "something_extra"], ["any"]),
            (["s_id", "start", "end", "gsd_id", "pre_ic", "ic", "min_vel", "tc"], ["segmented", "min_vel", "ic"]),
            (
                ["s_id", "start", "end", "gsd_id", "pre_ic", "ic", "min_vel", "tc", "something_extra"],
                ["segmented", "min_vel", "ic"],
            ),
            (["s_id", "start", "end", "gsd_id", "ic", "min_vel", "tc"], ["ic", "segmented"]),
            (["s_id", "start", "end", "gsd_id", "ic", "min_vel", "tc", "something_extra"], ["ic", "segmented"]),
        ),
    )
    def test_valid_versions(self, cols, stride_types_valid, stride_types, as_index):
        expected_outcome = stride_types in stride_types_valid or stride_types == "any"
        df = pd.DataFrame(columns=cols)
        if as_index:
            df = df.set_index("s_id")

        out = is_multi_sensor_stride_list({"s1": df}, stride_type=stride_types)

        assert expected_outcome == out

    def test_only_one_invalid(self):
        valid_cols = ["s_id", "start", "end", "gsd_id"]
        invalid_cols = ["start", "end", "gsd_id"]
        valid = {"s1": pd.DataFrame(columns=valid_cols)}
        invalid = {"s2": pd.DataFrame(columns=invalid_cols), **valid}

        assert is_multi_sensor_stride_list(valid)
        assert not is_multi_sensor_stride_list(invalid)

    def test_invalid_stride_type_argument(self):
        valid_cols = ["s_id", "start", "end", "gsd_id"]
        valid = {"s1": pd.DataFrame(columns=valid_cols)}

        with pytest.raises(ValueError):
            is_multi_sensor_stride_list(valid, stride_type="invalid_value")


class TestIsSingleSensorPositionList:
    @pytest.mark.parametrize(
        "value",
        (
            list(range(6)),
            "test",
            np.arange(6),
            {},
            pd.DataFrame(),
            pd.DataFrame(columns=[*range(3)]),
            pd.DataFrame(columns=["sample", "pos_x", "pos_y", "pos_z"]),
            pd.DataFrame(columns=["s_id", "sample", "pos_x", "pos_z"]),
        ),
    )
    def test_wrong_datatype(self, value):
        assert not is_single_sensor_position_list(value)

    @pytest.mark.parametrize(
        "cols, index",
        (
            (["s_id", "sample", "pos_x", "pos_y", "pos_z"], []),
            (["s_id", "sample", "pos_x", "pos_y", "pos_z", "something_else"], []),
            (["sample", "pos_x", "pos_y", "pos_z"], ["s_id"]),
            (["pos_x", "pos_y", "pos_z"], ["s_id", "sample"]),
            (["pos_x", "pos_y", "pos_z", "something_else"], ["s_id", "sample"]),
        ),
    )
    def test_valid_versions(self, cols, index):
        df = pd.DataFrame(columns=[*cols, *index])
        if index:
            df = df.set_index(index)

        assert is_single_sensor_position_list(df)

    @pytest.mark.parametrize(
        "cols, index, both",
        (
            (["s_id", "sample", "pos_x", "pos_y", "pos_z"], [], True),
            (["sample", "pos_x", "pos_y", "pos_z"], [], False),
            (["pos_x", "pos_y", "pos_z"], ["s_id", "sample"], True),
            (["pos_x", "pos_y", "pos_z"], ["sample"], False),
        ),
    )
    def test_valid_versions_without_s_id(self, cols, index, both):

        df = pd.DataFrame(columns=[*cols, *index])
        if index:
            df = df.set_index(index)

        assert is_single_sensor_position_list(df) == both
        assert is_single_sensor_position_list(df, s_id=False) is True


class TestIsSingleSensorOrientationList:
    @pytest.mark.parametrize(
        "value",
        (
            list(range(6)),
            "test",
            np.arange(6),
            {},
            pd.DataFrame(),
            pd.DataFrame(columns=[*range(3)]),
            pd.DataFrame(columns=["sample", "q_x", "q_y", "q_z", "q_w"]),
            pd.DataFrame(columns=["s_id", "sample", "qx", "qz", "qw"]),
        ),
    )
    def test_wrong_datatype(self, value):
        assert not is_single_sensor_orientation_list(value)

    @pytest.mark.parametrize(
        "cols, index",
        (
            (["s_id", "sample", "q_x", "q_y", "q_z", "q_w"], []),
            (["s_id", "sample", "q_x", "q_y", "q_z", "q_w", "something_else"], []),
            (["sample", "q_x", "q_y", "q_z", "q_w"], ["s_id"]),
            (["q_x", "q_y", "q_z", "q_w"], ["s_id", "sample"]),
            (["q_x", "q_y", "q_z", "q_w", "something_else"], ["s_id", "sample"]),
        ),
    )
    def test_valid_versions_with_s_id(self, cols, index):
        df = pd.DataFrame(columns=[*cols, *index])
        if index:
            df = df.set_index(index)

        assert is_single_sensor_orientation_list(df)

    @pytest.mark.parametrize(
        "cols, index, both",
        (
            (["s_id", "sample", "q_x", "q_y", "q_z", "q_w"], [], True),
            (["sample", "q_x", "q_y", "q_z", "q_w"], [], False),
            (["q_x", "q_y", "q_z", "q_w"], ["s_id", "sample"], True),
            (["q_x", "q_y", "q_z", "q_w"], ["sample"], False),
        ),
    )
    def test_valid_versions_without_s_id(self, cols, index, both):

        df = pd.DataFrame(columns=[*cols, *index])
        if index:
            df = df.set_index(index)

        assert is_single_sensor_orientation_list(df) == both
        assert is_single_sensor_orientation_list(df, s_id=False) is True


class TestIsMultiSensorPositionList:
    @pytest.mark.parametrize(
        "value", (list(range(6)), "test", np.arange(6), {}, pd.DataFrame(), pd.DataFrame(columns=[*range(3)])),
    )
    def test_wrong_datatype(self, value):
        assert not is_multi_sensor_position_list(value)

    @pytest.mark.parametrize(
        "cols, index",
        (
            (["s_id", "sample", "pos_x", "pos_y", "pos_z"], []),
            (["s_id", "sample", "pos_x", "pos_y", "pos_z", "something_else"], []),
            (["sample", "pos_x", "pos_y", "pos_z"], ["s_id"]),
            (["pos_x", "pos_y", "pos_z"], ["s_id", "sample"]),
            (["pos_x", "pos_y", "pos_z", "something_else"], ["s_id", "sample"]),
        ),
    )
    def test_valid_versions(self, cols, index):
        df = pd.DataFrame(columns=[*cols, *index])
        if index:
            df = df.set_index(index)

        assert is_multi_sensor_position_list({"s1": df})

    def test_only_one_invalid(self):
        valid_cols = ["s_id", "sample", "pos_x", "pos_y", "pos_z"]
        invalid_cols = ["sample", "pos_x", "pos_y", "pos_z"]
        valid = {"s1": pd.DataFrame(columns=valid_cols)}
        invalid = {"s2": pd.DataFrame(columns=invalid_cols), **valid}

        assert is_multi_sensor_position_list(valid)
        assert not is_multi_sensor_position_list(invalid)


class TestIsMultiSensorOrientationList:
    @pytest.mark.parametrize(
        "value", (list(range(6)), "test", np.arange(6), {}, pd.DataFrame(), pd.DataFrame(columns=[*range(3)])),
    )
    def test_wrong_datatype(self, value):
        assert not is_multi_sensor_orientation_list(value)

    @pytest.mark.parametrize(
        "cols, index",
        (
            (["s_id", "sample", "q_x", "q_y", "q_z", "q_w"], []),
            (["s_id", "sample", "q_x", "q_y", "q_z", "q_w", "something_else"], []),
            (["sample", "q_x", "q_y", "q_z", "q_w"], ["s_id"]),
            (["q_x", "q_y", "q_z", "q_w"], ["s_id", "sample"]),
            (["q_x", "q_y", "q_z", "q_w", "something_else"], ["s_id", "sample"]),
        ),
    )
    def test_valid_versions(self, cols, index):
        df = pd.DataFrame(columns=[*cols, *index])
        if index:
            df = df.set_index(index)

        assert is_multi_sensor_orientation_list({"s1": df})

    def test_only_one_invalid(self):
        valid_cols = ["s_id", "sample", "q_x", "q_y", "q_z", "q_w"]
        invalid_cols = ["sample", "q_x", "q_y", "q_z", "q_w"]
        valid = {"s1": pd.DataFrame(columns=valid_cols)}
        invalid = {"s2": pd.DataFrame(columns=invalid_cols), **valid}

        assert is_multi_sensor_orientation_list(valid)
        assert not is_multi_sensor_orientation_list(invalid)


class TestSetCorrectIndex:
    def test_no_change_needed(self):
        index_names = ["t1", "t2"]
        test = _create_test_multiindex()
        test = test.rename(index_names)
        df = pd.DataFrame(range(9), index=test, columns=["c"])

        assert_frame_equal(df, set_correct_index(df, index_names))

    @pytest.mark.parametrize("level", (0, 1, [0, 1]))
    def test_cols_to_index(self, level):
        """Test what happens if one or multiple of the expected index cols are normal cols."""
        index_names = ["t1", "t2"]
        test = _create_test_multiindex()
        test = test.rename(index_names)
        df = pd.DataFrame(range(9), index=test, columns=["c"])

        reset_df = df.reset_index(level=level)

        out = set_correct_index(reset_df, index_names)

        assert out.index.names == index_names
        # Nothing was changed besides setting the index
        assert_frame_equal(df, out)

    def test_col_does_not_exist(self):
        index_names = ["t1", "t2"]
        test = _create_test_multiindex()
        test = test.rename(index_names)
        df = pd.DataFrame(range(9), index=test, columns=["c"])

        with pytest.raises(KeyError):
            set_correct_index(df, ["does_not_exist", *index_names])

    @pytest.mark.parametrize("drop_additional", (True, False))
    def test_additional_index_col(self, drop_additional):
        index_names = ["t1", "t2"]
        test = _create_test_multiindex()
        test = test.rename(index_names)
        df = pd.DataFrame(range(9), index=test, columns=["c"])

        expected = ["t1", "c"]
        out = set_correct_index(df, expected, drop_false_index_cols=drop_additional)

        assert out.index.names == expected
        assert ("t2" in out.columns) is not drop_additional


class TestIsSingleRegionsOfInterestList:
    @pytest.mark.parametrize(
        "value",
        (
            list(range(6)),
            "test",
            np.arange(6),
            {},
            pd.DataFrame(),
            pd.DataFrame(columns=[*range(3)]),
            pd.DataFrame([[*range(9)]], columns=_create_test_multiindex()),
        ),
    )
    def test_wrong_datatype(self, value):
        assert not is_single_sensor_regions_of_interest_list(value)

    @pytest.mark.parametrize(
        "cols, roi_type_valid",
        (
            (["start", "end", "gs_id"], "gs"),
            (["start", "end", "gs_id", "something_extra"], "gs"),
            (["start", "end", "roi_id"], "roi"),
            (["start", "end", "roi_id", "something_extra"], "roi"),
        ),
    )
    def test_valid_versions(self, cols, roi_type_valid, roi_types):
        expected_outcome = roi_types in roi_type_valid or roi_types == "any"

        out = is_single_sensor_regions_of_interest_list(pd.DataFrame(columns=cols), region_type=roi_types)

        assert expected_outcome == out

    def test_invalid_region_type_argument(self):
        valid_cols = ["start", "end", "gs_id"]
        valid = pd.DataFrame(columns=valid_cols)

        with pytest.raises(ValueError):
            is_single_sensor_regions_of_interest_list(valid, region_type="invalid_value")

    @pytest.mark.parametrize("col_name", ("gs_id", "roi_id"))
    def test_identical_region_ids(self, col_name):
        """Test that the search for identical region ids works."""
        cols = [col_name, "start", "end"]
        roi_list = pd.DataFrame(columns=cols)
        roi_list[col_name] = np.array([1, 2, 2])
        expected_outcome = False

        out = is_single_sensor_regions_of_interest_list(roi_list, region_type="any")

        assert expected_outcome == out

    @pytest.mark.parametrize("col_name", ("gs_id", "roi_id"))
    def test_id_col_as_index(self, col_name):
        """Test that the id col can either be the index or a column."""
        cols = [col_name, "start", "end"]
        roi_list = pd.DataFrame(columns=cols)
        roi_list = roi_list.set_index(col_name)

        out = is_single_sensor_regions_of_interest_list(roi_list, region_type="any")

        assert out is True


class TestIsMultiSensorRegionsOfInterestList:
    @pytest.mark.parametrize(
        "value", (list(range(6)), "test", np.arange(6), {}, pd.DataFrame(), pd.DataFrame(columns=[*range(3)])),
    )
    def test_wrong_datatype(self, value):
        assert not is_multi_sensor_stride_list(value)

    @pytest.mark.parametrize(
        "cols, roi_type_valid",
        (
            (["start", "end", "gs_id"], "gs"),
            (["start", "end", "gs_id", "something_extra"], "gs"),
            (["start", "end", "roi_id"], "roi"),
            (["start", "end", "roi_id", "something_extra"], "roi"),
        ),
    )
    def test_valid_versions(self, cols, roi_type_valid, roi_types):
        expected_outcome = roi_types in roi_type_valid or roi_types == "any"

        out = is_multi_sensor_regions_of_interest_list({"s1": pd.DataFrame(columns=cols)}, region_type=roi_types)

        assert expected_outcome == out

    def test_only_one_invalid(self):
        valid_cols = ["gs_id", "start", "end"]
        invalid_cols = ["start", "end"]
        valid = {"s1": pd.DataFrame(columns=valid_cols)}
        invalid = {"s2": pd.DataFrame(columns=invalid_cols), **valid}

        assert is_multi_sensor_regions_of_interest_list(valid)
        assert not is_multi_sensor_regions_of_interest_list(invalid)

    def test_invalid_region_type_argument(self):
        valid_cols = ["start", "end", "gs_id"]
        valid = pd.DataFrame(columns=valid_cols)

        with pytest.raises(ValueError):
            is_multi_sensor_regions_of_interest_list({"si": valid}, region_type="invalid_value")
