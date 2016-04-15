"""Pre-processing module.

This module contains several pre-processing routines that can help
detect more patterns with PatternMatcher.

Classes included in this module are:
 - ShiftToMult: transform all left shifts of a constant in
   multiplications
 - all_preprocessings: apply all preprocessing transformations
"""

import ast
import copy
from tools import asttools, unparse


class ShiftToMult(ast.NodeTransformer):
    """
    Transform all left shifts of a constant in multiplications.
    """

    def visit_BinOp(self, node):
        'Change left shifts into multiplications'

        if not isinstance(node.op, ast.LShift):
            return self.generic_visit(node)
        if isinstance(node.right, ast.Num):
            self.generic_visit(node)
            return ast.BinOp(node.left, ast.Mult(), ast.Num(2**(node.right.n)))
        return self.generic_visit(node)


class SubToMult(ast.NodeTransformer):
    """
    Subs are a pain in the ass. Let's change them to *(-1)
    """

    def visit_BinOp(self, node):
        'Change operator - to a *(-1)'

        self.generic_visit(node)
        if isinstance(node.op, ast.Sub):
            node.op = ast.Add()
            const_mult_cond = (isinstance(node.right, ast.BinOp) and
                               isinstance(node.right.op, ast.Mult) and
                               isinstance(node.right.left, ast.Num))
            node.right = ast.BinOp(ast.Num(-1), ast.Mult(), node.right)
        return node

    def visit_UnaryOp(self, node):
        'Change -x to (-1)*x'

        self.generic_visit(node)
        if isinstance(node.op, ast.USub):
            node = ast.BinOp(ast.Num(-1), ast.Mult(), node.operand)
        return node


class NotToInv(ast.NodeTransformer):
    """
    Transform a (~X) in (- X - 1).
    """

    def visit_UnaryOp(self, node):
        'Change ~x to - x - 1'

        if isinstance(node.op, ast.Invert):
            return ast.BinOp(ast.UnaryOp(ast.USub(), node.operand),
                             ast.Add(),
                             ast.Num(-1))
        return self.generic_visit(node)


class RemoveUselessAnd(ast.NodeTransformer):
    """
    (A & 0xFF...FF) == A
    """

    def __init__(self, expr_ast, nbits):
        if not nbits:
            getsize = asttools.GetSize()
            getsize.visit(expr_ast)
            if getsize.result:
                nbits = getsize.result
            else:
                # default bitsize is 8
                nbits = 8
        self.nbits = nbits

    def visit_BinOp(self, node):
        'Change (A & 2**self.nbits - 1) in A'
        if isinstance(node.op, ast.BitAnd):
            if isinstance(node.right, ast.Num):
                if node.right.n != (2**self.nbits - 1):
                    return self.generic_visit(node)
                return self.generic_visit(node.left)
            if isinstance(node.left, ast.Num):
                if node.left.n != (2**self.nbits - 1):
                    return self.generic_visit(node)
                return self.generic_visit(node.right)
        return self.generic_visit(node)


def all_preprocessings(asttarget, nbits=0):
    'Apply all pre-processing transforms'
    asttarget = ShiftToMult().visit(asttarget)
    asttarget = SubToMult().visit(asttarget)
    asttarget = RemoveUselessAnd(asttarget, nbits).visit(asttarget)
    ast.fix_missing_locations(asttarget)
    return asttarget