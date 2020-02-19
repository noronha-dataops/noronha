# -*- coding: utf-8 -*-

from noronha.common.utils import am_i_on_board

__all__ = ['notebook', 'online']

if am_i_on_board():
    from noronha.tools.notebook import NoronhaEngine
