import torch
from torch import nn
from torch.nn import functional


import numpy as np


class RNNDecoder(nn.Module):
    """
    Decoder module of the sequence to sequence model.
    """

    def __init__(self,
                 hidden_size,
                 embedding_size,
                 recurrent_layer,
                 output_size,
                 learning_rate,
                 max_length,
                 num_layers,
                 use_cuda,
                 attention=None,
                 tf_ratio=0):
        """

        :param hidden_size:
        :param embedding_size:
        :param recurrent_layer:
        :param output_size:
        :param learning_rate:
        :param max_length:
        :param use_cuda:
        :param num_layers:
        :param attention:
        :param tf_ratio:
        """
        super(RNNDecoder, self).__init__()

        self.__use_cuda = use_cuda
        self.__hidden_size = hidden_size
        self.__output_size = output_size
        self.__num_layers = num_layers
        self.__max_length = max_length
        self.__tf_ratio = tf_ratio

        self.__attention = attention
        self.__embedding_layer = None

        if recurrent_layer == 'LSTM':
            unit_type = torch.nn.LSTM
        else:
            unit_type = torch.nn.GRU

        if attention is not None:
            input_size = self.__attention.input_size
        else:
            input_size = embedding_size

        self.__recurrent_layer = unit_type(input_size=input_size,
                                           hidden_size=self.__hidden_size,
                                           num_layers=self.__num_layers,
                                           bidirectional=False,
                                           batch_first=True)

        self.__output_layer = nn.Linear(self.__hidden_size, self.__output_size)

        if use_cuda:
            self.__recurrent_layer = self.__recurrent_layer.cuda()
            self.__output_layer = self.__output_layer.cuda()

        params = self.parameters()
        if attention is not None:
            self.__attention._recurrent_layer = self.__recurrent_layer
            params = list(list(params) + list(self.__attention.parameters()))

        self.__optimizer = torch.optim.Adam(params, lr=learning_rate)

    def _decode_step(self,
                     step_input,
                     hidden_state,
                     encoder_outputs,
                     batch_size,
                     sequence_length):
        """

        :param step_input:
        :param hidden_state:
        :param encoder_outputs:
        :param batch_size:
        :param sequence_length:
        :return:
        """
        embedded_input = self.embedding(step_input)

        output, hidden_state, attn_weights = self.__attention.forward(step_input=embedded_input,
                                                                      hidden_state=hidden_state,
                                                                      encoder_outputs=encoder_outputs,
                                                                      batch_size=batch_size,
                                                                      sequence_length=sequence_length)

        output = functional.log_softmax(self.__output_layer(output.contiguous().view(-1, self.__hidden_size)),
                                        dim=1).view(batch_size, -1, self.__output_size)

        return output, hidden_state, attn_weights

    def _decode(self,
                inputs,
                hidden_state,
                batch_size):
        """

        :param inputs:
        :param hidden_state:
        :param batch_size:
        :return:
        """
        embedded_inputs = self.embedding(inputs)
        outputs, hidden_state = self.__recurrent_layer(embedded_inputs, hidden_state)
        outputs = functional.log_softmax(self.__output_layer(outputs.contiguous().view(-1, self.__hidden_size)),
                                         dim=1).view(batch_size, -1, self.__output_size)

        return outputs, hidden_state

    def forward(self,
                inputs,
                encoder_outputs,
                lengths,
                hidden_state,
                loss_function,
                teacher_forcing_ratio=0):
        """

        :param inputs:
        :param encoder_outputs:
        :param lengths:
        :param hidden_state:
        :param loss_function:
        :param teacher_forcing_ratio:
        :return:
        """
        batch_size = inputs.size(0)
        sequence_length = inputs.size(1)
        decoded_lengths = np.zeros(batch_size)

        symbols = np.zeros((batch_size, sequence_length), dtype='int')

        use_teacher_forcing = True
        loss = 0
        if use_teacher_forcing:
            if self.__attention is not None:
                for step in range(sequence_length):
                    step_input = inputs[:, step].unsqueeze(-1)
                    step_output, hidden_state, attn_weights = self._decode_step(step_input=step_input,
                                                                                hidden_state=hidden_state,
                                                                                encoder_outputs=encoder_outputs,
                                                                                batch_size=batch_size,
                                                                                sequence_length=sequence_length)

                    loss += loss_function(step_output.squeeze(1), inputs[:, step])
                    symbols[:, step] = step_output.topk(1)[1].data.squeeze(-1).squeeze(-1).cpu().numpy()

            else:
                outputs, hidden_state = self._decode(inputs=inputs,
                                                     hidden_state=hidden_state,
                                                     batch_size=batch_size)

                for step in range(sequence_length):
                    symbols[:, step] = outputs[:, step, :].topk(1)[1].squeeze(-1).data.cpu().numpy()

                loss = loss_function(outputs.view(-1, self.__output_size), inputs.view(-1))

        else:
            step_output = inputs[:, 0]
            if self.__attention is not None:
                for step in range(sequence_length):
                    step_output, hidden_state = self._decode(step_input=step_output,
                                                             hidden_state=hidden_state,
                                                             batch_size=batch_size,
                                                             activation=functional.log_softmax)

                    if isinstance(hidden_state, tuple):
                        hidden_state = (self._attention(hidden_state[0], encoder_outputs), hidden_state[1])
                    else:
                        hidden_state = self._attention(hidden_state, encoder_outputs)

                    loss += loss_function(step_output.squeeze(1), inputs[:, step])
                    symbols[:, step] = step_output.topk(1)[1].data.squeeze(-1).squeeze(-1).cpu().numpy()

            else:
                for step in range(sequence_length):
                    step_output, hidden_state = self._decode(step_input=step_output,
                                                             hidden_state=hidden_state,
                                                             batch_size=batch_size,
                                                             activation=functional.log_softmax)

        return loss, symbols

    @property
    def optimizer(self):
        """

        :return:
        """
        return self.__optimizer

    @optimizer.setter
    def optimizer(self, optimizer):
        """

        :param optimizer:
        :return:
        """
        self.__optimizer = optimizer

    @property
    def output_dim(self):
        """

        :return:
        """
        return self.__output_size

    @property
    def embedding(self):
        """

        :return:
        """
        return self.__embedding_layer

    @embedding.setter
    def embedding(self, embedding):
        """

        :param embedding:
        :return:
        """
        self.__embedding_layer = nn.Embedding(embedding.size(0), embedding.size(1))
        self.__embedding_layer.weight = nn.Parameter(embedding)
        self.__embedding_layer.weight.requires_grad = False


class BeamDecoder:

    def __init__(self):
        pass


class ConvDecoder:

    def __init__(self):
        pass

