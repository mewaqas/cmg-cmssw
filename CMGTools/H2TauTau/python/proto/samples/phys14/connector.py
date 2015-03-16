import os
import pickle
import glob
import re

from CMGTools.RootTools.utils.splitFactor                   import splitFactor

from CMGTools.H2TauTau.proto.samples.phys14.higgs           import mc_higgs
from CMGTools.H2TauTau.proto.samples.phys14.ewk             import mc_ewk
from CMGTools.H2TauTau.proto.samples.phys14.diboson         import mc_diboson
from CMGTools.H2TauTau.proto.samples.phys14.triggers_tauMu  import mc_triggers as mc_triggers_mt
from CMGTools.H2TauTau.proto.samples.phys14.triggers_tauEle import mc_triggers as mc_triggers_et
from CMGTools.H2TauTau.proto.samples.phys14.triggers_tauTau import mc_triggers as mc_triggers_tt
from CMGTools.H2TauTau.proto.samples.phys14.triggers_muEle  import mc_triggers as mc_triggers_em

class httConnector(object):

    def __init__(self, tier, user, pattern, triggers,
                 production=False, splitFactor=10e4,
                 fineSplitFactor=4, cache=True, verbose=False):
        ''' '''
        if tier.startswith('%'):
            self.tier = tier
        else:
            self.tier = '%'+tier
        self.user            = user
        self.pattern         = pattern
        self.cache           = cache
        self.verbose         = verbose
        self.production      = production
        self.triggers        = triggers
        self.splitFactor     = splitFactor
        self.fineSplitFactor = fineSplitFactor
        self.homedir         = os.getenv('HOME')
        self.mc_dict         = {}
        self.MC_list         = []
        self.aliases         = aliases = {
                                          '/GluGluToHToTauTau.*Phys14DR.*' : 'HiggsGGH'         ,
                                          '/VBF_HToTauTau.*Phys14DR.*'     : 'HiggsVBF'         ,
                                          '/DYJetsToLL.*Phys14DR.*'        : 'DYJets'           ,
                                          '/TTJets.*Phys14DR.*'            : 'TTJets'           ,
                                          '/T_tW.*Phys14DR.*'              : 'T_tW'             ,
                                          '/Tbar_tW.*Phys14DR.*'           : 'Tbar_tW'          ,
                                          '/WZJetsTo3LNu.*Phys14DR.*'      : 'WZJetsTo3LNu'     ,
                                          '/TTbarH.*Phys14DR.*'            : 'HiggsTTHInclusive',
                                          '/WJetsToLNu.*Phys14DR.*'        : 'WJets'            ,
                                         }

        self.dictionarize_()
        self.listify_()

    def dictionarize_(self):
        ''' '''
        for s in mc_higgs + mc_ewk + mc_diboson:
            self.mc_dict[s.name] = s

    def listify_(self):
        ''' '''
        self.MC_list = [v for k, v in self.mc_dict.items()]
        for sam in self.MC_list:
            sam.splitFactor     = splitFactor(sam, self.splitFactor)
            sam.fineSplitFactor = self.fineSplitFactor
            if self.triggers == 'mt': sam.triggers = mc_triggers_mt
            if self.triggers == 'et': sam.triggers = mc_triggers_et
            if self.triggers == 'tt': sam.triggers = mc_triggers_tt
            if self.triggers == 'em': sam.triggers = mc_triggers_em

    def connect(self):
        '''Retrieves the relevant information
        (e.g. files location) for each component.
        To avoid multiple connections to the database
        is production == True, it checks for a cached
        pickle file containing all the info.

        FIXME! RIC: this should be done by default,
        but I make the use of the cached pickle explicit
        because the name of the parent dataset, and
        therefore the number of events and the
        computing efficiency, is not
        saved in the pickle file, and it can only be retrieved
        through a query to the database. This is
        necessary at the analysis level, but not at
        the production stage, where the only bit of info
        that's really needed is the location of the files.
        Should revisit the way the pickle file is saved
        so that ALL the relevant info is stored there.
        '''
        if self.production:
            self.connect_by_pck_()
        else:
            self.connect_by_db_()

        self.pruneSampleList_()

    def connect_by_db_(self):
        ''' '''
        from CMGTools.RootTools.utils.connect import connect
        connect(self.MC_list, self.tier, self.pattern,
                self.aliases, cache=self.cache, verbose=self.verbose)

    def connect_by_pck_(self):
        ''' '''
        from CMGTools.RootTools.utils.getFiles import getFiles

        redict_aliases = dict( zip(self.aliases.values(), self.aliases.keys()) )

        regex = re.compile(r'(?P<sample>[a-zA-Z0-9_]+[a-zA-Z])(?:[0-9]+)$')

        for alias_k, alias_v in self.mc_dict.items():
            m = regex.match(alias_k)
            if m:
                alias_k = m.group('sample')
            if alias_k not in self.aliases.values():
                continue
            sample_pkl = '*'.join(['',redict_aliases[alias_k].replace('/','').replace('.','*'),
                                   self.tier.replace('%',''),self.pattern+'.pck'])
            cached_sample = glob.glob('/'.join([self.homedir,'.cmgdataset',sample_pkl]))
            single_mc_list = [alias_v]

            if len(cached_sample) == 0:
                print 'sample not cached yet, connecting to the DB'
                from CMGTools.RootTools.utils.connect import connect
                connect(single_mc_list, self.tier, self.pattern, self.aliases,
                         cache=self.cache, verbose=self.verbose)

            elif len(cached_sample) >1:
                print 'better specify which sample, many found'
                print cached_sample
                raise

            else:
                file = open(cached_sample[0])
                mycomp = pickle.load(file)
                single_mc_list[0].files = getFiles('/'.join( ['']+mycomp.lfnDir.split('/')[mycomp.lfnDir.split('/').index('CMG')+1:] ),
                                                              mycomp.user, self.pattern, useCache=self.cache)

    def pruneSampleList_(self):
        self.MC_list = [m for m in self.MC_list if m.files]
