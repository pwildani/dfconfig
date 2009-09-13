"""
Miscellaneous utilities.
"""

SYMBOL_TABLE = {}
def Symbol(val):
  """Save ram by cashing strings here. Rather like intern."""
  return SYMBOL_TABLE.setdefault(val, val)


def declaration(impl):
  """Declare an @foo.

  This implements the behavior of allowing (keyword=) args without requiring
  them at the cost of disallowing positional args. A positional arg is assumed
  to be the target of the @foo.
  """
  def _declaration_impl(self, __target=None, **kwargs):
    if __target is not None:
      return impl(self, __target, **kwargs)
    return lambda __target: impl(self, __target, **kwargs)
  return _declaration_impl


def EnsureSubclass(superclass, target):
  """Force target to be a subclass of superclass."""
  if not issubclass(target, superclass):
      bases = list(target.__bases__)
      i = bases.index(object)
      bases[i:i] = [superclass]
      try:
        # Approach 1: inject superclass directly into __bases__
        target.__bases__ = tuple(bases)
        # Typical error: 
        # TypeError: __bases__ assignment: 'ObjectStartTag' deallocator differs
        # from 'object'
      except TypeError:
        # Approach 2: rebuild the class with a different bases list:
        # This has the drawback of not preserving target's identity.
        target = type(target.__name__,
                      tuple(bases),
                      dict(target.__dict__))
  assert issubclass(target, superclass)
  return target
