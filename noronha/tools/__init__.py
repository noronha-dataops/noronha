# -*- coding: utf-8 -*-

from noronha.bay.utils import am_i_on_board

__all__ = ['notebook', 'online']

if am_i_on_board():
    from noronha.tools.notebook import NoronhaEngine
