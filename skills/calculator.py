import ast
import operator
import logging

from skills.base import BaseSkill

log = logging.getLogger("zari")

ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


class CalculatorSkill(BaseSkill):
    priority = 60
    timeout = 5.0

    async def execute(self, query: str) -> dict | None:
        text = query.lower().strip()
        for kw in ["hisobla", "calculate", "necha", "qancha", "=", "boladi", "bo'ladi", "ni"]:
            text = text.replace(kw, "").strip()
        text = text.replace("x", "*").replace("×", "*").replace("÷", "/")
        text = text.replace("+", " + ").replace("-", " - ").replace("*", " * ").replace("/", " / ")
        text = " ".join(text.split())

        if not text:
            return None

        try:
            result = self._safe_eval(text)
            response = f"{text} = {result}"
            return {"response": response, "context": response, "source": "calculator"}
        except Exception:
            try:
                numbers = [s for s in text.split() if s.replace('.', '').replace('-', '').isdigit()]
                ops = [s for s in text.split() if s in '+-*/']
                if numbers and ops:
                    expr = ' '.join(numbers[i] + ' ' + ops[i] if i < len(ops) else numbers[i] for i in range(len(numbers)))
                    result = self._safe_eval(expr)
                    response = f"{expr} = {result}"
                    return {"response": response, "context": response, "source": "calculator"}
            except Exception:
                pass
            return None

    def _safe_eval(self, expr: str) -> float:
        tree = ast.parse(expr, mode="eval")
        return self._eval_node(tree.body)

    def _eval_node(self, node) -> float:
        if isinstance(node, ast.Constant):
            return float(node.value)
        if isinstance(node, ast.UnaryOp):
            op_func = ALLOWED_OPS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Ruxsatsiz operator: {type(node.op).__name__}")
            return op_func(self._eval_node(node.operand))
        if isinstance(node, ast.BinOp):
            op_func = ALLOWED_OPS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Ruxsatsiz operator: {type(node.op).__name__}")
            return op_func(self._eval_node(node.left), self._eval_node(node.right))
        raise ValueError(f"Ruxsatsiz ifoda: {type(node).__name__}")
