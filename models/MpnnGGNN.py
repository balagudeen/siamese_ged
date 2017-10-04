#!/usr/bin/python
# -*- coding: utf-8 -*-

from MessageFunction import MessageFunction
from UpdateFunction import UpdateFunction
from ReadoutFunction import ReadoutFunction

import torch
import torch.nn as nn
from torch.autograd import Variable

__author__ = "Pau Riba"
__email__ = "priba@cvc.uab.cat"


class MpnnGGNN(nn.Module):
    """
        MPNN as proposed by Li et al..

        This class implements the whole Li et al. model following the functions proposed by Gilmer et al. as
        Message, Update and Readout.

        Parameters
        ----------
        e : int list.
            Possible edge labels for the input graph.
        hidden_state_size : int
            Size of the hidden states (the input will be padded with 0's to this size).
        message_size : int
            Message function output vector size.
        n_layers : int
            Number of iterations Message+Update (weight tying).
        l_target : int
            Size of the output.
        type : str (Optional)
            Classification | [Regression (default)]. If classification, LogSoftmax layer is applied to the output vector.
    """

    def __init__(self, in_n, e, hidden_state_size, message_size, n_layers, l_target, type='regression'):
        super(MpnnGGNN, self).__init__()

        # Define message
        self.m = nn.ModuleList([MessageFunction('ggnn', args={'e_label': e, 'in': hidden_state_size, 'out': message_size})])

        # Define Update
        self.u = nn.ModuleList([UpdateFunction('ggnn',
                                                args={'in_m': message_size,
                                                'out': hidden_state_size})])

        # Define Readout
        self.r = ReadoutFunction('ggnn',
                                 args={'in': in_n[0],
                                       'hidden': hidden_state_size,
                                       'target': l_target})

        self.type = type

        self.args = {}
        self.args['out'] = hidden_state_size

        self.n_layers = n_layers

    def forward(self, g, h_in, e):

        # Padding to some larger dimension d
        h_t = torch.cat([h_in, Variable(
            torch.zeros(h_in.size(0), h_in.size(1), self.args['out'] - h_in.size(2)).type_as(h_in.data))], 2)

        # Layer
        for t in range(0, self.n_layers):
            e_aux = e.view(-1, e.size(3))

            h_aux = h_t.view(-1, h_t.size(2))

            m = self.m[0].forward(h_t, h_aux, e_aux)
            m = m.view(h_t.size(0), h_t.size(1), -1, m.size(1))

            # Nodes without edge set message to 0
            m = torch.unsqueeze(g, 3).expand_as(m) * m

            m = torch.squeeze(torch.sum(m, 1))

            h_t = self.u[0].forward(h_t, m)

            # Delete virtual nodes
            h_t = (h_in.abs().sum(2).expand_as(h_t) > 0).type_as(h_t) * h_t

        # Readout
        res = self.r.forward([h_t, h_in])

        if self.type == 'classification':
            res = nn.LogSoftmax()(res)
        return res

