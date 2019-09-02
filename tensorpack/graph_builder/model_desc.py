# -*- coding: utf-8 -*-
# File: model_desc.py


from collections import namedtuple
import tensorflow as tf

from ..utils.develop import log_deprecated, HIDE_DOC
from ..utils.argtools import memoized_method
from ..tfutils.common import get_op_tensor_name
from ..tfutils.tower import get_current_tower_context
from ..compat import backport_tensor_spec, tfv1

TensorSpec = backport_tensor_spec()


__all__ = ['InputDesc', 'ModelDesc', 'ModelDescBase']


class InputDesc(
        namedtuple('InputDescTuple', ['type', 'shape', 'name'])):
    """
    An equivalent of `tf.TensorSpec`.

    History: this concept is used to represent metadata about the inputs,
    which can be later used to build placeholders or other types of input source.
    It is introduced much much earlier than the equivalent concept `tf.TensorSpec`
    was introduced in TensorFlow.
    Therefore, we now switched to use `tf.TensorSpec`, but keep this here for compatibility reasons.
    """

    def __new__(cls, type, shape, name):
        """
        Args:
            type (tf.DType):
            shape (tuple):
            name (str):
        """
        log_deprecated("InputDesc", "Use tf.TensorSpec instead!", "2020-03-01")
        assert isinstance(type, tf.DType), type
        return tf.TensorSpec(shape=shape, dtype=type, name=name)


class ModelDescBase(object):
    """
    Base class for a model description.
    """

    @HIDE_DOC
    def get_inputs_desc(self):
        log_deprecated("ModelDesc.get_inputs_desc", "Use get_input_signature instead!", "2020-03-01")
        return self.get_input_signature()

    @memoized_method
    def get_input_signature(self):
        """
        Returns:
            A list of :class:`tf.TensorSpec`, which describes the inputs of this model.
            The result is cached for each instance of :class:`ModelDescBase`.
        """
        with tf.Graph().as_default() as G:   # create these placeholder in a temporary graph
            inputs = self.inputs()
            assert isinstance(inputs, (list, tuple)), \
                "ModelDesc.inputs() should return a list of tf.TensorSpec objects! Got {} instead.".format(str(inputs))
            if isinstance(inputs[0], tf.Tensor):
                for p in inputs:
                    assert "Placeholder" in p.op.type, \
                        "inputs() have to return TensorSpec or placeholders! Found {} instead.".format(p)
                    assert p.graph == G, "Placeholders returned by inputs() should be created inside inputs()!"
            return [TensorSpec(shape=p.shape, dtype=p.dtype, name=get_op_tensor_name(p.name)[0]) for p in inputs]

    @property
    def input_names(self):
        """
        list[str]: the names of all the inputs.
        """
        return [k.name for k in self.get_input_signature()]

    def inputs(self):
        """
        Returns a list of :class:`tf.TensorSpec` or placeholders.
        A subclass is expected to implement this method.

        If returning placeholders,
        the placeholders **have to** be created inside this method.
        Don't return placeholders created in other places.

        Also, you should never call this method by yourself.

        Returns:
            list[tf.TensorSpec or tf.placeholder]. To be converted to :class:`tf.TensorSpec`.
        """
        raise NotImplementedError()

    def build_graph(self, *args):
        """
        Build the whole symbolic graph.
        This is supposed to be part of the "tower function" when used with :class:`TowerTrainer`.

        A subclass is expected to implement this method.

        Args:
            args ([tf.Tensor]): tensors that matches the list of inputs defined by ``inputs()``.

        Returns:
            In general it returns nothing, but a subclass
            may require it to return necessary information to build the trainer.
            For example, `SingleCostTrainer` expect this method to return the cost tensor.
        """
        raise NotImplementedError()

    @property
    def training(self):
        """
        bool: whether the caller is under a training context or not.
        """
        return get_current_tower_context().is_training


class ModelDesc(ModelDescBase):
    """
    A ModelDesc with **single cost** and **single optimizer**.
    It has the following constraints in addition to :class:`ModelDescBase`:

    1. :meth:`build_graph(...)` method should return a cost when called under a training context.
       The cost will be the final cost to be optimized by the optimizer.
       Therefore it should include necessary regularization.

    2. Subclass is expected to implement :meth:`optimizer()` method.

    """

    @memoized_method
    def get_optimizer(self):
        """
        Return the memoized optimizer returned by `optimizer()`.

        Users of :class:`ModelDesc` will need to implement `optimizer()`,
        which will only be called once per each model.

        Returns:
            a :class:`tf.train.Optimizer` instance.
        """
        ret = self.optimizer()
        assert isinstance(ret, tfv1.train.Optimizer), \
            "ModelDesc.optimizer() must return a tf.train.Optimizer! Got {} instead.".format(str(ret))
        return ret

    def optimizer(self):
        """
        Returns a `tf.train.Optimizer` instance.
        A subclass is expected to implement this method.
        """
        raise NotImplementedError()
