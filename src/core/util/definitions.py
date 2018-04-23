import os

from src.config import HorusConfig

config = HorusConfig()
if config.root_dir == '':
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
else:
    ROOT_DIR = config.root_dir

RUN_TAGGER_CMD = config.models_tweetnlp_java_param + " -jar " + config.models_tweetnlp_jar + " --model " + config.models_tweetnlp_model

NER_RITTER_PER = ['B-person', 'I-person']
NER_RITTER_ORG = ['B-company', 'I-company']
NER_RITTER_LOC = ['B-geo-loc', 'I-geo-loc']

NER_STANFORD_PER = ['PERSON']
NER_STANFORD_ORG = ['ORGANIZATION', 'GSP'] # GSP = geo-political social group
NER_STANFORD_LOC = ['LOCATION']

NER_NLTK_PER = ['B-PERSON', 'I-PERSON', 'PERSON']
NER_NLTK_ORG = ['B-ORGANIZATION', 'I-ORGANIZATION', 'ORGANIZATION', 'GSP']
NER_NLTK_LOC = ['B-LOCATION', 'I-LOCATION', 'LOCATION', 'GPE'] # GPE = geo-political entities such as city, state/province, and country

NER_CONLL_PER = ['I-PER']
NER_CONLL_ORG = ['I-ORG']
NER_CONLL_LOC = ['I-LOC'] # GPE = geo-political entities such as city, state/province, and country

NER_TAGS_PER = ['PER']
NER_TAGS_PER.extend(NER_RITTER_PER)
NER_TAGS_PER.extend(NER_STANFORD_PER)
NER_TAGS_PER.extend(NER_NLTK_PER)
NER_TAGS_PER.extend(NER_CONLL_PER)

NER_TAGS_ORG = ['ORG']
NER_TAGS_ORG.extend(NER_RITTER_ORG)
NER_TAGS_ORG.extend(NER_STANFORD_ORG)
NER_TAGS_ORG.extend(NER_NLTK_ORG)
NER_TAGS_ORG.extend(NER_CONLL_ORG)

NER_TAGS_LOC = ['LOC']
NER_TAGS_LOC.extend(NER_RITTER_LOC)
NER_TAGS_LOC.extend(NER_STANFORD_LOC)
NER_TAGS_LOC.extend(NER_NLTK_LOC)
NER_TAGS_LOC.extend(NER_CONLL_LOC)

#TODO: check if we have here ALL the NOUNs!!!
# merge of ALL noun tags, from all the POS taggers

# Penn Treebank
POS_NOUN_PTB = ['NN', 'NNS', 'NNP', 'NNPS', 'PRP', 'PRP$']
POS_NOUN_UNIVERSAL = ['NOUN', 'PRON', 'PROPN']

POS_NOUN_TAGS = []
POS_NOUN_TAGS.extend(POS_NOUN_PTB)
POS_NOUN_TAGS.extend(POS_NOUN_UNIVERSAL)

NER_RITTER = []
NER_RITTER.extend(NER_RITTER_PER)
NER_RITTER.extend(NER_RITTER_ORG)
NER_RITTER.extend(NER_RITTER_LOC)

NER_CONLL = []
NER_CONLL.extend(NER_CONLL_PER)
NER_CONLL.extend(NER_CONLL_ORG)
NER_CONLL.extend(NER_CONLL_LOC)

NER_TAGS = []
NER_TAGS.extend(NER_TAGS_ORG)
NER_TAGS.extend(NER_TAGS_PER)
NER_TAGS.extend(NER_TAGS_LOC)

KLASSES = {1: "LOC", 2: "ORG", 3: "PER", 4: "O"}
KLASSES2 = {"LOC": 1, "ORG": 2, "PER": 3, "O": 4}

HORUS_MATRIX_HEADER = ["IS_NAMED_ENTITY", "ID_SENT", "ID_WORD", "TOKEN", "POS_UNI", "POS", "NER", "COMPOUND",
    "COMPOUND_SIZE", "ID_TERM_TXT", "ID_TERM_IMG", "TOT_IMG", "TOT_CV_LOC", "TOT_CV_ORG",
    "TOT_CV_PER", "DIST_CV_I", "PL_CV_I", "NR_RESULTS_SE_IMG", "KLASS_PREDICT_CV", "TOT_RESULTS_TX", "TOT_TX_LOC",
    "TOT_TX_ORG", "TOT_TX_PER", "TOT_ERR_TRANS", "DIST_TX_I", "NR_RESULTS_SE_TX", "KLASS_PREDICT_TX",
    "FEATURE_EXTRA_1", "FEATURE_EXTRA_2", "FEATURE_EXTRA_3", "FEATURE_EXTRA_4", "FEATURE_EXTRA_5", "FEATURE_EXTRA_6",
    "FEATURE_EXTRA_7", "FEATURE_EXTRA_8", "FEATURE_EXTRA_9", "KLASS_1", "KLASS_2", "KLASS_3", "KLASS_4",
    "KLASS_5", "KLASS_6", "KLASS_7", "KLASS_8", "KLASS_9", "KLASS_10", "KLASS_11", "KLASS_12", "KLASS_13",
    "KLASS_14", "KLASS_15", "KLASS_REAL"]

CMU_PENN_TAGS = [['N', 'NNS'], ['O', 'PRP'], ['S', 'PRP$'], ['^', 'NNP'], ["D", "DT"], ["A", "JJ"], ["P", "IN"],
                     ["&", "CC"],["V", "VBD"], ["R", "RB"], ["!", "UH"], ["T", "RP"], ["$", "CD"], ['G', 'SYM']]

CMU_UNI_TAGS = [["N", "NOUN"], ["^", "NOUN"], ["V", "VERB"], ["D", "DET"], ["A", "ADJ"], ["P", "ADP"],
                        ["&", "CCONJ"], ["R", "ADV"], ["!", "INTJ"], ["O","PRON"], ["$", "NUM"], [",", "PUNCT"]]

PENN_UNI_TAG = [['#', 'SYM'],['$', 'SYM'], ['','PUNCT'],[',','PUNCT'],['-LRB-','PUNCT'],['-RRB-','PUNCT'],['.','PUNCT'],[':','PUNCT'],	['AFX','ADJ'],
                    ['CC','CONJ'],['CD','NUM'],['DT','DET'],['EX','ADV'],['FW','X'],['HYPH','PUNCT'],['IN','ADP'],['JJ','ADJ'],	['JJR','ADJ'],['JJS','ADJ'],
                    ['LS','PUNCT'],['MD','VERB'],['NIL','X'],['NN','NOUN'],	['NNP','PROPN'],['NNPS','PROPN'],['NNS','NOUN'],['PDT','DET'],['POS','PART'],
                    ['PRP','PRON'],['PRP$','DET'],['RB','ADV'],['RBR','ADV'],['RBS','ADV'],['RP','PART'],['SYM','SYM'],['TO','PART'],['UH','INTJ'],['VB','VERB'],
                    ['VBD','VERB'],['VBG','VERB'],['VBN','VERB'],['VBP','VERB'],['VBZ','VERB'],['WDT','DET'],['WP','PRON'],['WP$', 'DET'],['WRB', 'ADV']]


HORUS_FORMAT_INDEX_COL_IS_ENTITY = 0
HORUS_FORMAT_INDEX_COL_ID_SENTENCE = 1
HORUS_FORMAT_INDEX_COL_ID_WORD = 2
HORUS_FORMAT_INDEX_COL_WORD = 3
HORUS_FORMAT_INDEX_COL_POS_UNI = 4
HORUS_FORMAT_INDEX_COL_POS = 5
HORUS_FORMAT_INDEX_COL_NER = 6
HORUS_FORMAT_INDEX_COL_IS_COMPOUND = 7
HORUS_FORMAT_INDEX_COL_COMPOUND_SIZE = 8
HORUS_FORMAT_INDEX_COL_ID_TERM_TXT = 9
HORUS_FORMAT_INDEX_COL_ID_TERM_IMG = 10
HORUS_FORMAT_INDEX_COL_TOT_IMG = 11
HORUS_FORMAT_INDEX_COL_TOT_CV_LOC = 12
HORUS_FORMAT_INDEX_COL_TOT_CV_ORG = 13
HORUS_FORMAT_INDEX_COL_TOT_CV_PER = 14
HORUS_FORMAT_INDEX_COL_DIST_CV_I = 15
HORUS_FORMAT_INDEX_COL_PL_CV_I= 16
HORUS_FORMAT_INDEX_COL_NR_RESULTS_SE_IMG = 17
HORUS_FORMAT_INDEX_COL_KLASS_PREDICT_CV = 18
HORUS_FORMAT_INDEX_COL_TOT_RESULTS_TX = 19
HORUS_FORMAT_INDEX_COL_TOT_TX_LOC = 20
HORUS_FORMAT_INDEX_COL_TOT_TX_ORG = 21
HORUS_FORMAT_INDEX_COL_TOT_TX_PER = 22
HORUS_FORMAT_INDEX_COL_TOT_ERR_TRANS = 23
HORUS_FORMAT_INDEX_COL_DIST_TX_I = 24
HORUS_FORMAT_INDEX_COL_NR_RESULTS_SE_TX = 25
HORUS_FORMAT_INDEX_COL_TX_KLASS = 26
HORUS_FORMAT_INDEX_COL_INDEX_START_TERM = 27
HORUS_FORMAT_INDEX_COL_FEATURE_EXTRA_02 = 28
HORUS_FORMAT_INDEX_COL_FEATURE_EXTRA_03 = 29
HORUS_FORMAT_INDEX_COL_FEATURE_EXTRA_04 = 30
HORUS_FORMAT_INDEX_COL_FEATURE_EXTRA_05 = 31
HORUS_FORMAT_INDEX_COL_FEATURE_EXTRA_06 = 32
HORUS_FORMAT_INDEX_COL_FEATURE_EXTRA_07 = 33
HORUS_FORMAT_INDEX_COL_FEATURE_EXTRA_08 = 34
HORUS_FORMAT_INDEX_COL_FEATURE_EXTRA_09 = 35
HORUS_FORMAT_INDEX_COL_KLASS_01 = 36
HORUS_FORMAT_INDEX_COL_KLASS_02 = 37
HORUS_FORMAT_INDEX_COL_KLASS_03 = 38
HORUS_FORMAT_INDEX_COL_KLASS_04 = 39
HORUS_FORMAT_INDEX_COL_KLASS_05 = 40
HORUS_FORMAT_INDEX_COL_KLASS_06 = 41
HORUS_FORMAT_INDEX_COL_KLASS_07 = 42
HORUS_FORMAT_INDEX_COL_KLASS_08 = 43
HORUS_FORMAT_INDEX_COL_KLASS_09 = 44
HORUS_FORMAT_INDEX_COL_KLASS_10 = 45
HORUS_FORMAT_INDEX_COL_KLASS_11 = 46
HORUS_FORMAT_INDEX_COL_KLASS_12 = 47
HORUS_FORMAT_INDEX_COL_KLASS_13 = 48
HORUS_FORMAT_INDEX_COL_KLASS_14 = 49
HORUS_FORMAT_INDEX_COL_KLASS_15 = 50
HORUS_FORMAT_INDEX_COL_TARGET_NER = 51

HORUS_TOT_FEATURES = 52
