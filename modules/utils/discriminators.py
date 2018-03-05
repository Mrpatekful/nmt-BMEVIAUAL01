from ..base.discriminator import Discriminator

import torch
import torch.nn as nn


class MLPDiscriminator(Discriminator):  # TODO
    """

    """

    def __init__(self,
                 input_dim,
                 hidden_dim,
                 learning_rate,
                 use_cuda):
        """

        :param input_dim:
        :param hidden_dim:
        :param learning_rate:
        :param use_cuda:
        """
        super().__init__()

        self._input_layer = nn.Linear(input_dim, hidden_dim)
        self._hidden_layer = nn.Linear(hidden_dim, hidden_dim)
        self._output_layer = nn.Linear(hidden_dim, 1)
        self._activation = nn.LeakyReLU()

        if use_cuda:
            self._input_layer = self._input_layer.cuda()
            self._hidden_layer = self._hidden_layer.cuda()
            self._output_layer = self._output_layer.cuda()
            self._activation = self._activation.cuda()

        self._optimizer = torch.optim.RMSprop(self.parameters(), lr=learning_rate)

    def forward(self,
                inputs,
                input_dim,
                hidden_dim,
                learning_rate):
        """

        :param inputs:
        :param input_dim:
        :param hidden_dim:
        :param learning_rate:
        :return:
        """
        output = self._activation(self._input_layer(inputs))
        output = self._activation(self._hidden_layer(output))
        output = self._activation(self._output_layer(output))
        return output

    @property
    def optimizer(self):
        """

        :return:
        """
        return self._optimizer

    @optimizer.setter
    def optimizer(self, optimizer):
        """

        :param optimizer:
        :return:
        """
        self._optimizer = optimizer


class RNNDiscriminator(Discriminator):  # TODO
    """

    """

    def __init__(self,
                 input_dim,
                 hidden_dim,
                 learning_rate,
                 use_cuda):
        """

        :param input_dim:
        :param hidden_dim:
        :param learning_rate:
        :param use_cuda:
        """
        super().__init__()

    def forward(self,
                inputs,
                input_dim,
                hidden_dim,
                learning_rate):
        """

        :param inputs:
        :param input_dim:
        :param hidden_dim:
        :param learning_rate:
        :return:
        """
        return NotImplementedError