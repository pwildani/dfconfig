import df_syntax

C = df_syntax.DFConfigSyntaxHelper()
NewTag = C.NewTag
def GetObjectType(typename):
  return C._df_object_types[typename]

# Bootstrap the OBJECT mode switch tag.
@C.tag
class OBJECT(df_syntax.Tag):
  def __init__(self, tokens):
    df_syntax.Tag.__init__(self, tokens)

    # Generic OBJECT == TAG
    if self.ObjectType() not in C._df_object_types:
      self.DeclareGenericObjectType(self.ObjectType())
  
  def ObjectType(self):
    return self.tokens[1]

  def DeclareGenericObjectType(self, objectname):

    @C.df_object(name=objectname)
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


# DESCRIPTOR objects start with the COLOR or SHAPE tags
@C.df_object
class DESCRIPTOR:
  @C.start_tag
  class COLOR: pass
  @C.start_tag
  class SHAPE: pass

# ITEM objects start with the ITEM_* tags
@C.df_object
class ITEM:
  @C.start_tag
  class ITEM_AMMO: pass

  @C.start_tag
  class ITEM_ARMOR: pass

  @C.start_tag
  class ITEM_FOOD: pass

  @C.start_tag
  class ITEM_GLOVES: pass

  @C.start_tag
  class ITEM_HELM: pass

  @C.start_tag
  class ITEM_INSTRUMENT: pass

  @C.start_tag
  class ITEM_PANTS: pass

  @C.start_tag
  class ITEM_SHIELD: pass

  @C.start_tag
  class ITEM_SHOES: pass

  @C.start_tag
  class ITEM_SIEGEAMMO: pass

  @C.start_tag
  class ITEM_TOY: pass

  @C.start_tag
  class ITEM_TRAPCOMP: pass

  @C.start_tag
  class ITEM_WEAPON: pass


# MATGLOSS objects start with the MATGLOSS_* tags
@C.df_object
class MATGLOSS:
  @C.start_tag
  class MATGLOSS_METAL: pass

  @C.start_tag
  class MATGLOSS_PLANT: pass

  @C.start_tag
  class MATGLOSS_STONE: pass

  @C.start_tag
  class MATGLOSS_WOOD: pass



# LANGUAGE objects start with TRANSLATION, SYMBOL, or WORD tags
@C.df_object
class LANGUAGE:
  @C.start_tag
  class TRANSLATION: pass

  @C.start_tag
  class SYMBOL: pass

  @C.start_tag
  class WORD: pass


# BODY startswith both BODY and BODYGLOSS
@C.df_object
class BODY:
  @C.start_tag
  class BODY: pass

  @C.start_tag
  class BODYGLOSS: pass

  @C.section
  class BP: pass


# TODO: [CREATURE][ATTACK]. Might be hard to do without listing all of the non-attack creature tags.
