import math


def safe_eval(expression: str) -> str:
    try:
        expr = expression.strip()
        if not expr:
            return '0'

        namespace = {
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log10,
            'ln': math.log,
            'sqrt': math.sqrt,
            'pow': math.pow,
            'pi': math.pi,
            'e': math.e,
            'factorial': math.factorial,
            'abs': abs,
            'radians': math.radians,
            'degrees': math.degrees,
        }

        code = compile(expr, '<calc>', 'eval')
        for name in code.co_names:
            if name not in namespace:
                raise NameError(f"'{name}' is not allowed")

        result = eval(code, {'__builtins__': {}}, namespace)

        if isinstance(result, complex):
            return 'Error: Complex result'

        if isinstance(result, float):
            if result == float('inf') or result == float('-inf'):
                return 'Error: Overflow'
            if math.isnan(result):
                return 'Error: Invalid Operation'
            if abs(result) < 1e-12:
                result = 0.0
            formatted = f'{result:.12f}'.rstrip('0').rstrip('.')
            return formatted if formatted else '0'

        return str(result)

    except ZeroDivisionError:
        return 'Error: Division by zero'
    except (SyntaxError, TypeError, ValueError, NameError):
        return 'Error: Invalid Expression'
    except OverflowError:
        return 'Error: Overflow'
    except Exception:
        return 'Error'
