"""
Author: vivekraghuram <vivek.raghuram@berkeley.edu>
"""

from IPython import embed
from nluas.language.core_specializer import *
import os

dir_name = os.path.dirname(os.path.realpath(__file__))


class WinogradSpecializer(CoreSpecializer):

    def __init__(self, analyzer_port):
        CoreSpecializer.__init__(self, analyzer_port)

        self.parameter_templates = {}
        self.mood_templates = {}
        self.descriptor_templates = {}
        self.event_templates = {}
        self.initialize_templates()

        # Used and maintained by the resolver step
        self.bridging_schemas = OrderedDict()
        self.RDs = OrderedDict()
        self.unresolved_RDs = []

        self.bridge_rules = {
            "thanks"        : "TransitiveAction",
            "response"      : "Communication",
            "repetition"    : "Communication"
        }

    def initialize_templates(self):
        self.parameter_templates = self.read_templates(
            os.path.join(dir_name, "parameter_templates.json"))
        self.mood_templates = self.read_templates(
            os.path.join(dir_name, "mood_templates.json"))
        self.descriptor_templates = self.read_templates(
            os.path.join(dir_name, "descriptors.json"))
        self.event_templates = self.read_templates(
            os.path.join(dir_name, "event_templates.json"))

    # CORE OVERRIDES BELOW

    def specialize(self, fs):
        self.crawl_schemas(fs)
        self.resolve_bridging_schemas(fs)
        #self.resolve_referents_2(fs)

        # housekeeping
        self.bridging_schemas = {}
        self.RDs = {}
        self.unresolved_RDs = []
        return CoreSpecializer.specialize(self, fs)

    def crawl_schemas(self, fs):
        """
        Finds all bridging schemas, RDs and unresolved RDs in the semspec
        fs: FeatureStruct
        """
        stack = [([], "m", fs.m)]
        index_cache = set()

        while len(stack) > 0:
            parents, name, value = stack.pop()
            index_cache.add(value.__index__)
            if value.typesystem() == "SCHEMA":
                if self.analyzer.issubtype("SCHEMA", value.type(), "BridgeSchema"):
                    self.set_bridging_schema(value, parents + [name])
                if self.analyzer.issubtype("SCHEMA", value.type(), "RD"):
                    try:
                        unresolved = value.referent.type() == "antecedent"
                        self.set_RD(value, parents + [name], unresolved)
                    except:
                        pass
            if value.has_filler():
                for child_name, child_value in value.__items__():
                    if child_value.__index__ not in index_cache:
                        stack.append((parents + [name], child_name, child_value))


    def resolve_bridging_schemas(self, fs):
        """
        Attempts to match bridging schemas to other schemas in the semspec and use them to resolve
        referents
        fs: FeatureStruct
        """
        if len(self.bridging_schemas) == 0 or len(self.unresolved_RDs) == 0:
            return

        stack = [('m', fs.m)]
        index_cache = set()

        while len(stack) > 0:
            name, value = stack.pop()
            index_cache.add(value.__index__)

            if value.typesystem() == "SCHEMA" and not self.analyzer.issubtype("SCHEMA", value.type(), "BridgeSchema"):
                key = self.match_bridging_schema(fs, value)
                if key != None:
                    del self.bridging_schemas[key]
            if value.has_filler():
                for child_name, child_value in value.__items__():
                    if child_value.__index__ not in index_cache:
                        stack.append((child_name, child_value))

    def resolve_referents_2(self, fs):
        """
        Resolves remaining unresolved RDs
        fs: FeatureStruct
        """
        raise NotImplementedError()

    def set_bridging_schema(self, value, parents):
        """
        Stores the bridging schema
        value: Struct representing the schema
        parents: list of strings in order of parents from original FeatureStruct
        """
        index = value.__index__
        if index not in self.bridging_schemas:
            self.bridging_schemas[index] = (value, parents)

    def match_bridging_schema(self, fs, schema):
        """
        Matches the first bridging schema for which schema is a subtype if such a match exists
        fs: FeatureStruct of full semspec
        schema: Struct of a schema
        return: index/key of matched bridging schema or None
        """
        hypothesis, matched_index = None, None

        for index in self.bridging_schemas.keys():
            bridge, parents = self.bridging_schemas[index]
            if self.analyzer.issubtype("SCHEMA", schema.type(), self.bridge_rules[bridge.kind.type()]):
                parent = fs
                is_parent = False
                for parent_name in parents:
                    if parent.__index__ != schema.__index__: # I probably can't use an equality check here. Would need to use indices
                        parent = getattr(parent, parent_name)
                    else:
                        is_parent = True
                        break

                if is_parent:
                    continue

                # this is an ugly way to store entailments. FIXME
                entailments = {}

                if bridge.kind.type() == "thanks":
                    entailments = [
                        (getattr(schema, 'agent'), getattr(bridge, 'bridgeAgent')),
                        (getattr(schema, 'patient'), getattr(bridge, 'bridgePatient'))
                    ]
                elif bridge.kind.type() in ["response", "repetition"]:
                    entailments = [
                        (getattr(bridge, 'bridgeAgent'), getattr(schema, 'speaker')),
                        (getattr(bridge, 'bridgePatient'), getattr(schema, 'listener')),
                        (getattr(bridge, 'bridgeTheme'), getattr(schema, 'media'))
                    ]
                else:
                    embed()
                    Exception("Cannot have a bridging schema with kind %s", bridge.kind.type())
                # for bridge_name, bridge_value in bridge.__items__():
                #     if bridge_value.typesystem() == "SCHEMA" and self.analyzer.issubtype("SCHEMA", bridge_value.type(), "RD"):
                #         if getattr(schema, bridge_name).__index__ in self.unresolved_RDs:
                #             new_entailment = (getattr(schema, bridge_name), bridge_value)
                #             if new_entailment[0].__index__ not in entailments:
                #                 entailments[new_entailment[0].__index__] = new_entailment

                if self.valid_resolution(entailments):
                    self.assign_RDs(entailments)
                    return index

        return None

    def set_RD(self, value, parents, unresolved):
        """
        Stores the RD
        value: Struct representing the RD
        parents: list of strings in order of parents from original FeatureStruct
        unresolved: boolean for whether the RD is unresolved or not
        """
        index = value.__index__
        if index not in self.RDs:
            self.RDs[index] = (value, parents)
            if unresolved:
                self.unresolved_RDs.append(index)

    def valid_resolution(self, entailments):
        """
        Checks if a referent resolution is valid
        entailments: list of pairs (unresolved_RD, RD)
        return: Boolean
        """
        # TODO: Add more rules to avoid bad resolution like some of the transitive action heurisitcs
        for pronoun, ref in entailments:
            if not self.is_compatible_referents(pronoun, ref):
                return False
        return True

    def is_compatible_referents(self, pronoun, ref):
        for key, value in pronoun.__items__():
            if hasattr(ref, key) and key != "referent" and (value and getattr(ref, key)):
                if not self.is_compatible("ONTOLOGY", value.type(), getattr(ref, key).type()):
                    return False
        return True

    def assign_RDs(self, assignments):
        """
        Assigns the pronouns to be the value of their referents
        assignments: list of pairs (unresolved_RD, RD)
        """
        # I don't think this is the right way to resolve bindings. I shouldn't edit the schema
        for pronoun, ref in assignments:
            pronoun.__features__[pronoun.__index__] = pronoun.__features__[ref.__index__]
            if pronoun.__index__ in self.unresolved_RDs:
                self.unresolved_RDs.remove(pronoun.__index__)
