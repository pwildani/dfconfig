"""
Miscellaneous utilities.
"""

class Registry(dict):
  """Map name -> object, with an @decl."""
  def __init__(self, name):
    self.name = name

  def __call__(self, target=None, name=None):
    def _declaration(impl):
      if name is None:
        thename = impl.__name__
      else:
        thename = name
      self[thename] = impl
      return impl
    if target is not None:
      return _declaration(target)
    _declaration.__name__ = self.name
    return _declaration


SYMBOL_TABLE = {}
def Symbol(val):
  """Save ram by cashing strings here. Rather like intern."""
  return SYMBOL_TABLE.setdefault(val, val)


def EnsureSubclass(superclass, target):
  # Force target to be a subclass of superclass
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
