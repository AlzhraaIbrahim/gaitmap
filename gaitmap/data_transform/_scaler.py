"""Transformers that scale data to certaind ata ranges."""
from typing import Dict, Union, Tuple, Sequence, Set, Optional

import numpy as np
import pandas as pd
from tpcp import OptimizableParameter, PureParameter, Parameter
from typing_extensions import Self

from gaitmap.base import _BaseSerializable
from gaitmap.utils._types import _Hashable
from gaitmap.utils.datatype_helper import SensorData, SingleSensorData


class BaseTransformer(_BaseSerializable):
    """Base class for all data transformers."""

    action_methods = ('transform',)

    transformed_data_: SingleSensorData

    def transform(self, data: SingleSensorData, **kwargs) -> Self:
        """Transform the data using the transformer.

        Parameters
        ----------
        data
            A dataframe representing single sensor data.
        sampling_rate_hz
            The sampling rate of the data in Hz

        Returns
        -------
        transformed_data
            The transformed data

        """
        raise NotImplementedError()


class TrainableTransformerMixin(_BaseSerializable):
    """Mixin for transformers with adaptable parameters."""

    def self_optimize(self, data: Sequence[SingleSensorData], **kwargs) -> Self:
        """Learn the parameters of the transformer based on provided data.

        Parameters
        ----------
        data
           A sequence of dataframes, each representing single-sensor data.
        sampling_rate_hz
            The sampling rate of the data in Hz

        Returns
        -------
        self
            The trained instance of the transformer

        """
        raise NotImplementedError()


class GroupedTransformer(BaseTransformer, TrainableTransformerMixin):
    """Apply specific transformations to specific groups of columns.

    Parameters
    ----------
    transformer_mapping
        Dict to define which transformers should be applied to which columns.
        The key can either be the name of the column or a tuple of column names.
        The value, must be a transformer instance.
        If the transformer is trainable, its `self_optimize` method will be called, when `self_optimize` of the
        Grouped Transformer is called.
        The transformer will be cloned before that and hence, you can provide the same instance of a transformer
        multiple times in the mapping.
    keep_all_cols
        If `True`, columns that are not mentioned as keys in the `transformer_mapping`, will be added to the output
        unchanged.
        Otherwise, only columns that are actually transformed remain in the output.

    """
    transformer_mapping: OptimizableParameter[Dict[Union[_Hashable, Tuple[_Hashable, ...]], BaseTransformer]]
    keep_all_cols: PureParameter[bool]

    def __init__(
        self,
        transformer_mapping: Dict[Union[_Hashable, Tuple[_Hashable, ...]], BaseTransformer],
        keep_all_cols: bool = False,
    ):
        self.transformer_mapping = transformer_mapping
        self.keep_all_cols = keep_all_cols

    def self_optimize(self, data: Sequence[SingleSensorData], **kwargs) -> Self:
        """Train all trainable transformers based on the provided data.

        ... note :: All transformers will get only the data-columns for training that they are applied to.
                    If a transformer is listed multiple times in `transformer_mapping` it will be called multiple times,
                    with only the respective columns.
                    This means you might get different results when using `{("col_a", "col_b"):
                    transformer_instance}` compared to `{"col_a": transformer_instance, "col_b": transformer_instance},
                    because in the latter case, two different trained versions of the transformer will be created.

        Parameters
        ----------
        data
           A sequence of dataframes, each representing single-sensor data.
        sampling_rate_hz
            The sampling rate of the data in Hz

        Returns
        -------
        self
            The trained instance of the transformer

        """
        mapped_cols = self._validate_mapping()
        for d in data:
            self._validate(d, mapped_cols)
        for k, v in self.transformer_mapping.items():
            if isinstance(v, TrainableTransformerMixin):
                col_select = k
                if not isinstance(col_select, tuple):
                    col_select = (col_select,)
                self.transformer_mapping[k] = v.clone().self_optimize(
                    [d[list(col_select)] for d in data], **kwargs
                )
        return self

    def transform(self, data: SingleSensorData, **kwargs) -> SingleSensorData:
        """Transform all data columns based on the selected scalers."""
        mapped_cols = self._validate_mapping()
        self._validate(data, mapped_cols)
        results = {}
        mapping = self.transformer_mapping
        if self.keep_all_cols:
            mapping = {**mapping, **{k: IdentityTransformer() for k in set(data.columns) - mapped_cols}}
        for k, v in mapping.items():
            if not isinstance(k, tuple):
                k = (k,)
            tmp = v.transform(data[list(k)], **kwargs)
            for col in k:
                results[col] = tmp[[col]]
        self.transformed_data_ = pd.concat(results, axis=1)[data.columns]
        return self

    def _validate_mapping(self) -> Set[_Hashable]:
        # Check that each column is only mentioned once:
        unique_k = []
        for k in self.transformer_mapping.keys():
            if not isinstance(k, tuple):
                k = (k,)
            for i in k:
                if i in unique_k:
                    raise ValueError(
                        "Each column name must only be mentioned once in the keys of `scaler_mapping`."
                        "Applying multiple transformations to the same column is not supported."
                    )
                unique_k.append(i)
        return set(unique_k)

    def _validate(self, data: SingleSensorData, selected_cols: Set[_Hashable]):  # noqa: no-self-use
        if not set(data.columns).issuperset(selected_cols):
            raise ValueError("You specified transformations for columns that do not exist. This is not supported!")


class IdentityTransformer(BaseTransformer):
    """Dummy Transformer that does not modify the data."""

    def transform(self, data: SingleSensorData, **_) -> Self:
        self.transformed_data_ = data
        return self


class FixedScaler(BaseTransformer):
    """Apply a fixed scaling and offset to the data.

    The transformed data y is calculated as:

    .. code-block::

        y = (x - offset) / scale

    Parameters
    ----------
    scale
        Downscaling factor of the data.
        The data is divided by this value
    offset
        The offset that should be subtracted from the data.

    """

    scale: Parameter[float]
    offset: Parameter[float]

    def __init__(self, scale: float = 1, offset: float = 0):
        self.scale = scale
        self.offset = offset

    def transform(self, data: SingleSensorData, **_) -> Self:
        """Scale the data.

        Parameters
        ----------
        data
            A dataframe representing single sensor data.
        sampling_rate_hz
            The sampling rate of the data in Hz

        Returns
        -------
        transformed_data
            The scaled dataframe

        """
        self.transformed_data_ = (data - self.offset) / self.scale
        return self


class AbsMaxScaler(BaseTransformer):
    """Scale data by its absolute maximum.

    The data y after the transform is calculated as

    .. code-block::

        y = x * feature_max / max(abs(x))

    Note that the maximum over **all** columns is calculated.
    I.e. Only a single global scaling factor is applied to all the columns.

    Parameters
    ----------
    feature_max
        The value the maximum will be scaled to.
        After scaling the absolute maximum in the data will be equal to this value.
        Note that if the absolute maximum corresponds to a minimum in the data, this minimum will be scaled to
        `-feature_max`.

    """

    feature_max: Parameter[float]

    def __init__(self, feature_max: float = 1):
        self.feature_max = feature_max

    def transform(self, data: SingleSensorData, **_) -> Self:
        """Scale the data.

        Parameters
        ----------
        data
            A dataframe representing single sensor data.

        Returns
        -------
        transformed_data
            The scaled dataframe

        """
        self.transformed_data_ = self._transform(data, self._get_abs_max(data))
        return self

    def _get_abs_max(self, data: SingleSensorData) -> float:  # noqa: no-self-use
        return float(np.nanmax(np.abs(data.to_numpy())))

    def _transform(self, data: SingleSensorData, absmax: float) -> SingleSensorData:
        data = data.copy()
        data *= self.feature_max / absmax
        return data

    def self_optimize(self, data: Sequence[SingleSensorData]) -> Self:
        """Calculate scaling parameters based on a trainings sequence.

        Parameters
        ----------
        data
           A sequence of dataframes, each representing single-sensor data.
        sampling_rate_hz
            The sampling rate of the data in Hz

        Returns
        -------
        self
            The trained instance of the transformer

        """
        max_vals = [self._get_abs_max(d) for d in data]
        self.feature_max = np.max(max_vals)
        return self


class TrainableAbsMaxScaler(AbsMaxScaler, TrainableTransformerMixin):
    """Scale data by the absolut max of a trainings sequence.

    .. warning :: By default, this scaler will not modify the data!
                  Use `self_optimize` to adapt the `data_max` parameter based on a set of training data.

    During training the scaler will calculate the absolute max from the trainigs data,
    Per provided dataset `data_max` will be calculated.
    The final `data_max` is the max over all train sequences.

    .. code-block::

        data_max = max(abs(x_train))

    Note that the maximum over **all** columns is calculated.
    I.e. Only a single global scaling factor is applied to all the data.

    During transformation, this fixed scaling factor is applied to any new columns.

    .. code-block::

        y = x * feature_max / data_max

    """
    data_max: OptimizableParameter[Optional[float]]

    def __init__(self, feature_max: float = 1, data_max: Optional[float] = None):
        self.data_max = data_max
        super().__init__(feature_max=feature_max)

    def self_optimize(self, data: Sequence[SingleSensorData], **_) -> Self:
        """Calculate scaling parameters based on a trainings sequence.

        Parameters
        ----------
        data
           A sequence of dataframes, each representing single-sensor data.

        Returns
        -------
        self
            The trained instance of the transformer

        """
        max_vals = [self._get_abs_max(d) for d in data]
        self.data_max = np.max(max_vals)
        return self

    def transform(self, data: SingleSensorData, **_) -> Self:
        """Scale the data.

        Parameters
        ----------
        data
            A dataframe representing single sensor data.
        sampling_rate_hz
            The sampling rate of the data in Hz

        Returns
        -------
        transformed_data
            The scaled dataframe

        """
        if self.data_max is None:
            raise ValueError("data_max not set. Use self_optimize to learn it based on a trainings sequence.")
        self.transformed_data_ = self._transform(data, self.data_max)
        return self


class MinMaxScaler(BaseTransformer):
    """Scale the data by its Min-Max values.

    After the scaling the min of the data is equivalent ot `feature_range[0]` and the max of the data is equivalent
    to `feature_range[1]`.
    The output y is calculated as follows:

    .. code-block::

        scale = (feature_range[1] - feature_range[0]) / (x.min(), x.max())
        offset = feature_range[0] - x.min() * transform_scale
        y = x * scale + offset

    Note that the minimum and maximum over **all** columns is calculated.
    I.e. Only a single global scaling factor is applied to all the columns.

    """
    feature_range: Parameter[Tuple[float, float]]

    def __init__(
        self,
        feature_range: Tuple[float, float] = (0, 1.0),
    ):
        self.feature_range = feature_range

    def transform(self, data: SingleSensorData, **_) -> Self:
        """Scale the data.

        Parameters
        ----------
        data
            A dataframe representing single sensor data.
        sampling_rate_hz
            The sampling rate of the data in Hz

        Returns
        -------
        transformed_data
            The scaled dataframe

        """
        data_range = self._calc_data_range(data)
        self.transformed_data_ = self._transform(data, data_range)
        return self

    def _calc_data_range(self, data: SensorData) -> Tuple[float, float]:  # noqa: no-self-use
        # We calculate the global min and max over all rows and columns!
        data = data.to_numpy()
        return float(np.nanmin(data)), float(np.nanmax(data))

    def _transform(self, data: SingleSensorData, data_range: Tuple[float, float]) -> SingleSensorData:
        data = data.copy()
        feature_range = self.feature_range
        data_min, data_max = data_range
        transform_range = (data_max - data_min) or 1.0
        transform_scale = (feature_range[1] - feature_range[0]) / transform_range
        transform_min = feature_range[0] - data_min * transform_scale

        data *= transform_scale
        data += transform_min
        return data


class TrainableMinMaxScaler(MinMaxScaler, TrainableTransformerMixin):
    """Scale the data by Min-Max values learned from trainings data.

    .. warning :: By default, this scaler will not modify the data!
                  Use `self_optimize` to adapt the `data_range` parameter based on a set of training data.

    During training the scaling and offset is calculated based on the min and max of the trainings sequence.
    If multiple sequences are provided for training, the global min and max values of **all** sequences are used.

    .. code-block::

        data_range =  (x_train.min(), x_train.max())
        scale = (feature_range[1] - feature_range[0]) / (data_range[1] - data_range[0])
        offset = feature_range[0] - x_train.min() * transform_scale

    Note that the minimum and maximum over **all** columns is calculated.
    I.e. Only a single global scaling factor is applied to all the columns.

    During `transform` these trained transformation are applied as follows.

    .. code-block::

        y = x * scale + offset

    """
    feature_range = OptimizableParameter[Optional[Tuple[float, float]]]

    def __init__(
        self,
        feature_range: Tuple[float, float] = (0, 1.0),
        data_range: Optional[Tuple[float, float]] = None,
    ):
        self.data_range = data_range
        super().__init__(feature_range=feature_range)

    def self_optimize(self, data: Sequence[SingleSensorData], **_):
        """Calculate scaling parameters based on a trainings sequence.

        Parameters
        ----------
        data
           A sequence of dataframes, each representing single-sensor data.
        sampling_rate_hz
            The sampling rate of the data in Hz

        Returns
        -------
        self
            The trained instance of the transformer

        """
        mins, maxs = zip(*(self._calc_data_range(d) for d in data))
        self.data_range = np.min(mins), np.maxs(maxs)
        return self

    def transform(self, data: SingleSensorData, **_) -> SingleSensorData:
        """Scale the data.

        Parameters
        ----------
        data
            A dataframe representing single sensor data.
        sampling_rate_hz
            The sampling rate of the data in Hz

        Returns
        -------
        transformed_data
            The scaled dataframe

        """
        if self.data_range is None:
            raise ValueError("No data range set. Use self_optimize to learn it based on a trainings sequence.")
        return self._transform(data, data_range=self.data_range)
