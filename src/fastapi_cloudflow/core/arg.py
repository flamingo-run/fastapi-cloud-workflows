from __future__ import annotations

import json


class ArgExpr:
    def __init__(self, expr: str) -> None:
        self.expr = expr

    @staticmethod
    def _coerce_expr(value: str | ArgExpr) -> str:
        if isinstance(value, ArgExpr):
            return value.expr
        return f'"{value}"'

    def __truediv__(self, other: str | ArgExpr) -> ArgExpr:
        if isinstance(other, ArgExpr):
            right = other.expr
            return ArgExpr(f'{self.expr} + "/" + {right}')
        else:
            return ArgExpr(f'{self.expr} + "/{other}"')

    def __add__(self, other: str | ArgExpr) -> ArgExpr:
        right = self._coerce_expr(other)
        return ArgExpr(f"{self.expr} + {right}")

    def __str__(self) -> str:
        return f"${{{self.expr}}}"


class Arg:
    @staticmethod
    def env(name: str) -> ArgExpr:
        return ArgExpr(f'sys.get_env("{name}")')

    @staticmethod
    def param(path: str) -> ArgExpr:
        return ArgExpr(f"params.{path}")

    @staticmethod
    def ctx(key: str) -> ArgExpr:
        return ArgExpr(f"ctx.{key}")

    @staticmethod
    def expr(expression: str) -> ArgExpr:
        return ArgExpr(expression)

    @staticmethod
    def base64(value: str | ArgExpr) -> ArgExpr:
        inner = value.expr if isinstance(value, ArgExpr) else json.dumps(value)
        return ArgExpr(f"base64.encode({inner})")
