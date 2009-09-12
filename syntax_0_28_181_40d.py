"""The raws syntax for Dwarf Fortress version 0.28.181.40d."""

import df_syntax
from collections import defaultdict

C = df_syntax.DFConfigSyntaxHelper()

def NewToplevelTag(tokens):
  if tokens[0] == 'OBJECT':
    return OBJECT(tokens)
  return df_syntax.Tag(tokens)

# Bootstrap the OBJECT mode switch tag.
class OBJECT(df_syntax.Tag):
  def __init__(self, tokens):
    df_syntax.Tag.__init__(self, tokens)

    # Generic OBJECT == TAG
    if self.ObjectType() not in self.OBJECT_TYPES:
      self.DeclareGenericObjectType(self.ObjectType())

  OBJECT_TYPES = defaultdict(list)
  OBJECT_START_TAGS = defaultdict(dict)
  OBJECT_START_TAG_NAMES = defaultdict(dict)

  @classmethod
  def register(cls, typename, name=None):
    def _register(impl):
      impl = C.df_object(impl)
      cls.OBJECT_TYPES[typename].append(impl)
      if not impl.START_TAGS:
        # Force a default start tag named after the object type
        thename = name or impl.__name__
        impl.START_TAGS = [C.start_tag(type(thename, (), {}))]
      for tagtype in impl.START_TAGS:
        cls.OBJECT_START_TAG_NAMES[typename][tagtype.__name__] = tagtype
        cls.OBJECT_START_TAGS[typename][tagtype.__name__] = impl
      return impl
    return _register

  def IsStartTag(self, tag):
    return tag.TagName() in self.StartTags()

  def StartTags(self):
    return self.OBJECT_START_TAGS[self.ObjectType()]

  def Instantiate(self, tag):
    return self.StartTags()[tag.TagName()](tag)

  def NewTag(self, tokens):
    try:
      return self.OBJECT_START_TAG_NAMES[self.ObjectType()][tokens[0]](tokens)
    except KeyError:
      return None
  
  def ObjectType(self):
    return self.tokens[1]

  def DeclareGenericObjectType(self, objectname):
    @self.register(typename=objectname, name=objectname)
    class _Object(df_syntax.DFObject):

      @C.start_tag(name=objectname)
      class StartTag:
        MAX_TOKENS = 2
        MIN_TOKENS = 2

        def ObjectType(self):
          return self.tokens[0]

        def ObjectIdentifier(self):
          return self.tokens[1]
      StartTag.__name__ = objectname

    _Object.__name__ = objectname


# DESCRIPTOR objects are COLOR or SHAPE
DESCRIPTOR = OBJECT.register('DESCRIPTOR')
@DESCRIPTOR
class COLOR: pass

@DESCRIPTOR
class SHAPE: pass

# ITEM objects are all of the many ITEM_*s.
ITEM = OBJECT.register('ITEM')
@ITEM
class ITEM_AMMO: pass

@ITEM
class ITEM_ARMOR: pass

@ITEM
class ITEM_FOOD: pass

@ITEM
class ITEM_GLOVES: pass

@ITEM
class ITEM_HELM: pass

@ITEM
class ITEM_INSTRUMENT: pass

@ITEM
class ITEM_PANTS: pass

@ITEM
class ITEM_SHIELD: pass

@ITEM
class ITEM_SHOES: pass

@ITEM
class ITEM_SIEGEAMMO: pass

@ITEM
class ITEM_TOY: pass

@ITEM
class ITEM_TRAPCOMP: pass

@ITEM
class ITEM_WEAPON: pass


# MATGLOSS objects are all of the various MATGLOSS_*
MATGLOSS = OBJECT.register('MATGLOSS')

@MATGLOSS
class MATGLOSS_METAL: pass

@MATGLOSS
class MATGLOSS_PLANT: pass

@MATGLOSS
class MATGLOSS_STONE: pass

@MATGLOSS
class MATGLOSS_WOOD: pass



# LANGUAGE objects are TRANSLATION, SYMBOL, or WORD
LANGUAGE = OBJECT.register('LANGUAGE')

@LANGUAGE
class TRANSLATION: pass

@LANGUAGE
class SYMBOL: pass

@LANGUAGE
class WORD: pass


# BODY objects are BODY and BODYGLOSS
BODY = OBJECT.register('BODY')
@BODY
class BODY:

  @C.section
  class BP:
    """The BodyPart section."""

@BODY
class BODYGLOSS: pass


# TODO: [CREATURE][ATTACK]. Might be hard to do without listing all of the
# non-attack creature tags.
