# -*- coding: utf-8 -*-
"""
api/index.py — ponto de entrada esperado pela Vercel para funções Python.

A Vercel procura, por padrão, um app WSGI dentro de arquivos na pasta /api.
Este arquivo apenas importa o app Flask "de verdade", que continua definido
em app.py na raiz do projeto (assim ele funciona igual tanto localmente
quanto na Vercel).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402,F401
