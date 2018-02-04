# -*- coding: utf-8 -*-

"""
==========================================================
HORUS: Named Entity Recognition Algorithm
==========================================================

HORUS is a Named Entity Recognition Algorithm specifically
designed for short-text, i.e., microblogs and other noisy
datasets existing on the web, e.g.: social media, some web-
sites, blogs and etc..

It is a simplistic approach based on multi-level machine
learning combined with computer vision techniques.

more info at: https://github.com/dnes85/components-models

"""

# Author: Esteves <diegoesteves@gmail.com>
# Version: 1.0
# Version Label: HORUS_NER_2016_1.0
# License: BSD 3 clause
import csv
import heapq
import json
import logging
import re
import sqlite3
import string
import unicodedata
from time import gmtime, strftime

import nltk
import numpy
import pandas as pd
import requests
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from nltk.tokenize import sent_tokenize
from sklearn.externals import joblib

from horus.core.config import HorusConfig
from horus.core.util.nlp_tools import NLPTools
from horus.core.training.object_detection import CNN
from horus.core.training.object_detection import SIFT
from horus.core.search_engines import query_bing, query_flickr, query_wikipedia
from horus.core.util.sqlite_helper import SQLiteHelper, HorusDB
from horus.core.util.systemlog import SystemLog
from horus.core.util.definitions_sql import *
# print cv2.__version__
from horus.core.training.text_classification.bow_tfidf import BowTfidf
from horus.core.training.text_classification.topic_modeling import TopicModeling
from horus.core.translation.bingtranslation import BingTranslator
from horus.core.util import definitions


class Training(object):
    """ Description:
            A core module for training the algorithm
        Attributes:
            None
    """

    def __init__(self):
        self.sys = SystemLog("horus.log", logging.DEBUG, logging.DEBUG)
        self.config = HorusConfig()
        self.sys.log.info('------------------------------------------------------------------')
        self.sys.log.info('::                       HORUS ' + self.version + '                            ::')
        self.sys.log.info('------------------------------------------------------------------')
        self.sys.log.info(':: loading components...')
        self.tools = NLPTools()
        self.translator = BingTranslator()
        self.horus_matrix = []
        self.cnn = CNN()
        self.sift = SIFT()
        self.bow = BowTfidf()
        self.text_topicmodeling = TopicModeling()
        self.final = joblib.load(self.config.model_final)
        self.final_encoder = joblib.load(self.config.model_final_encoder)
        self.conn = sqlite3.connect(self.config.database_db)

        if bool(int(self.config.models_force_download)) is True:
            try:
                nltk.data.find('averaged_perceptron_tagger.zip')
            except LookupError:
                nltk.download('averaged_perceptron_tagger')
            try:
                nltk.data.find('punkt.zip')
            except LookupError:
                nltk.download('punkt')
            try:
                nltk.data.find('maxent_ne_chunker.zip')
            except LookupError:
                nltk.download('maxent_ne_chunker')
            try:
                nltk.data.find('universal_tagset.zip')
            except LookupError:
                nltk.download('universal_tagset')
            try:
                nltk.data.find('words.zip')
            except LookupError:
                nltk.download('words')

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.conn.close()
        except:
            pass

    ########################################### pre-processing ###########################################

    def __tokenize_and_pos(self, sentence, annotator_id):
        # NLTK
        if annotator_id == 1:
            return self.tools.tokenize_and_pos_nltk(sentence)
        # Stanford
        elif annotator_id == 2:
            return self.tools.tokenize_and_pos_stanford(sentence)
        # TwitterNLP
        elif annotator_id == 3:
            if type(sentence) is not list:
                return self.tools.tokenize_and_pos_twitter(sentence)
            return self.tools.tokenize_and_pos_twitter_list(sentence)

    def __sentence_cached_before(self, corpus, sentence):
        """This method caches the structure of HORUS in db
        in order to speed things up. The average pre-processing time is about to 4-5sec
        for EACH sentence due to attached components (eg.: stanford tools). If the sentence
        has already been cached, we load and convert strings to list, appending the content
        directly to the matrix, thus optimizing a lot this phase.
        """
        sent = []
        try:
            self.conn.text_factory = str
            sSql = """SELECT sentence_has_NER, 
            sentence, same_tokenization_nltk, same_tokenization_stanford, same_tokenization_tweetNLP,
            corpus_tokens, annotator_nltk_tokens, annotator_stanford_tokens, annotator_tweetNLP_tokens,
            corpus_ner_y, annotator_nltk_ner, annotator_stanford_ner, annotator_tweetNLP_ner,
            corpus_pos_y, annotator_nltk_pos, annotator_stanford_pos, annotator_tweetNLP_pos,
            corpus_pos_uni_y, annotator_nltk_pos_universal, annotator_stanford_pos_universal, annotator_tweetNLP_pos_universal,
            annotator_nltk_compounds, annotator_stanford_compounds, annotator_tweetNLP_compounds
            FROM HORUS_SENTENCES
            WHERE sentence = ? and corpus_name = ?"""
            c = self.conn.execute(sSql, (sentence, corpus))
            ret = c.fetchone()
            if ret is not None:
                sent.append(ret[0])
                sent.append([ret[1], ret[2], ret[3], ret[4]])
                sent.append([json.loads(ret[5]), json.loads(ret[6]), json.loads(ret[7]), json.loads(ret[8])])
                sent.append([json.loads(ret[9]), json.loads(ret[10]), json.loads(ret[11]), json.loads(ret[12])])
                sent.append([json.loads(ret[13]), json.loads(ret[14]), json.loads(ret[15]), json.loads(ret[16])])
                sent.append([json.loads(ret[17]), json.loads(ret[18]), json.loads(ret[19]), json.loads(ret[20])])
                sent.append([json.loads('[]'), json.loads(ret[21]), json.loads(ret[22]), json.loads(ret[23])])
        except Exception as e:
            self.sys.log.error(':: an error has occurred: ', e)
            raise
        return sent

    def __process_ds_conll_format(self, dspath, dataset_name, token_index, ner_index, separator='\t'):
        '''
        return a set of sentences
        :param dspath: path to Ritter dataset
        :return: sentence contains any entity?, sentence, words, NER tags
        '''
        try:
            # sentences
            sentences = []
            # default corpus tokens
            tokens = []
            # correct corpus NER tags
            tags_ner_y = []
            s = ''
            has3NER = -1
            tot_sentences = 1
            self.sys.log.info(':: processing sentences...')

            #hack to find problems in CONLL file
            #linenr = 0
            #with open(dspath) as f:
            #    for line in f:
            #        linenr+=1
            #        if line.strip() != '':
            #            if len(line.split()) != 2:
            #                print(linenr)
            #exit(0)

            with open(dspath) as f:
                for line in f:
                    if line.strip() != '':
                        if separator == '': separator = None
                        token = line.split(separator)[token_index]
                        ner = line.split(separator)[ner_index].replace('\r', '').replace('\n', '')
                    if line.strip() == '':
                        if len(tokens) != 0:
                            self.sys.log.debug(':: processing sentence %s' % str(tot_sentences))
                            sentences.append(
                                self.process_and_save_sentence(has3NER, s, dataset_name, tokens, tags_ner_y))
                            tokens = []
                            tags_ner_y = []
                            s = ''
                            has3NER = -1
                            tot_sentences += 1
                    else:
                        s += token + ' '
                        tokens.append(token)
                        tags_ner_y.append(ner)
                        if ner in definitions.NER_RITTER:
                            has3NER = 1

            self.sys.log.info(':: %s sentences processed successfully' % str(len(sentences)))
            return sentences
        except Exception as error:
            self.sys.log.error('caught this error: ' + repr(error))

    def __processing_conll_ds(self, dspath):
        sentences = []
        w = []
        t = []
        p = []
        pu = []
        c = []
        s = ''
        has3NER = -1
        with open(dspath) as f:
            for line in f:
                text = line.split(' ')
                token = text[0].replace('\n', '')
                if token == '':
                    if len(w) != 0:
                        sentences.append([has3NER, s, w, t, p, pu, c])
                        w = []
                        t = []
                        p = []
                        pu = []
                        c = []
                        s = ''
                        has3NER = -1
                else:
                    pos_tag = text[1]
                    chunck_tag = text[2]
                    ner_tag = text[3].replace('\n', '')
                    s += token + ' '
                    w.append(token)
                    p.append(pos_tag)
                    pu.append(self.tools.convert_penn_to_universal_tags(pos_tag))
                    t.append(ner_tag)
                    c.append(chunck_tag)
                    if ner_tag in definitions.NER_CONLL:
                        has3NER = 1
        return sentences

    def __get_compounds(self, tokens):
        compounds = []
        pattern = """
                                    NP:
                                       {<JJ>*<NN|NNS|NNP|NNPS><CC>*<NN|NNS|NNP|NNPS>+}
                                       {<NN|NNS|NNP|NNPS><IN>*<NN|NNS|NNP|NNPS>+}
                                       {<JJ>*<NN|NNS|NNP|NNPS>+}
                                       {<NN|NNP|NNS|NNPS>+}
                                    """
        cp = nltk.RegexpParser(pattern)
        toparse = []
        for token in tokens:
            toparse.append(tuple([token[0], token[1]]))
        t = cp.parse(toparse)

        i_word = 0
        for item in t:
            if type(item) is nltk.Tree:
                i_word += len(item)
                if len(item) > 1:  # that's a compound
                    compound = ''
                    for tk in item:
                        compound += tk[0] + ' '

                    compounds.append([i_word - len(item) + 1, compound[:len(compound) - 1], len(item)])
            else:
                i_word += 1
        return compounds

    def __process_and_save_sentence(self, hasNER, s, dataset_name='', tokens_gold_standard=[], ner_gold_standard=[]):
        # that' a sentence, check if cached!
        cache_sent = self.__sentence_cached_before(dataset_name, s)
        if len(cache_sent) != 0:
            return cache_sent
        else:

            _tokens_nltk, _pos_nltk, _pos_uni_nltk = self.__tokenize_and_pos(s, 1)
            _tokens_st, _pos_st, _pos_uni_st = self.__tokenize_and_pos(s, 2)
            _tokens_twe, _pos_twe, _pos_uni_twe = self.__tokenize_and_pos(s, 3)

            _pos_nltk = numpy.array(_pos_nltk)
            _pos_uni_nltk = numpy.array(_pos_uni_nltk)
            _pos_st = numpy.array(_pos_st)
            _pos_uni_st = numpy.array(_pos_uni_st)
            _pos_twe = numpy.array(_pos_twe)
            _pos_uni_twe = numpy.array(_pos_uni_twe)

            # nltk tok has the same length of corpus tok?
            _same_tok_nltk = (len(_tokens_nltk) == len(tokens_gold_standard))

            # stanford tok has the same length of corpus tok?
            _same_tok_stanf = (len(_tokens_st) == len(tokens_gold_standard))

            # tweetNLP tok has the same length of corpus tok?
            _same_tok_tweet = (len(_tokens_twe) == len(tokens_gold_standard))

            # NLTK NER
            nernltktags = self.tools.annotate_ner_nltk(_pos_nltk)

            # stanford NER
            nerstantags = self.tools.annotate_ner_stanford(s)
            nerstantags = numpy.array(nerstantags)

            comp_nltk = self.__get_compounds(_pos_nltk)
            comp_st = self.__get_compounds(_pos_st)
            comp_twe = self.__get_compounds(_pos_twe)

            # saving to database (pos_uni_sta not implemented yet)
            sent = [hasNER,
                    [s, 1 if _same_tok_nltk else 0, 1 if _same_tok_stanf else 0, 1 if _same_tok_tweet else 0],
                    [tokens_gold_standard, _tokens_nltk, _tokens_st, _tokens_twe],
                    [ner_gold_standard, nernltktags, nerstantags[:, 1].tolist(), []],
                    [[], _pos_nltk[:, 1].tolist(), _pos_st[:, 1].tolist(), _pos_twe[:, 1].tolist()],
                    [[], _pos_uni_nltk[:, 1].tolist(), [], _pos_uni_twe[:, 1].tolist()],
                    [[], comp_nltk, comp_st, comp_twe]
                    ]

            self.__db_save_sentence(sent, dataset_name)
            return sent

    def __process_input_text(self, text):
        self.sys.log.info(':: text: ' + text)
        self.sys.log.info(':: tokenizing sentences ...')
        sent_tokenize_list = sent_tokenize(text)
        self.sys.log.info(':: processing ' + str(len(sent_tokenize_list)) + ' sentence(s).')
        sentences = []
        for sentence in sent_tokenize_list:
            sentences.append(self.__process_and_save_sentence(-1, sentence))

        return sentences

    def __get_ner_mapping_simple(self, y, x, ix, starty):
        try:
            index = -1
            for k in range(starty, len(y)):
                base = y[k]
                for i in range(ix, len(x)):
                    term = x[i]
                    if self.config.models_pos_tag_lib == 1:  # nltk
                        term = x[i].replace('``', u'"')

                    swap = ''
                    if self.config.models_pos_tag_lib != 3:
                        if term == "''": swap = '"'
                        if term == '"': swap = "''"
                    # tweetNLP
                    # if u'&amp;amp;amp;amp;amp;amp;amp;amp;amp;amp;lt' == x[i]:
                    #    term = term.replace(u'&amp;amp;amp;amp;amp;amp;amp;amp;amp;amp;lt', u'&lt;')
                    # elif u'&' in x[i]:
                    #    term = term.replace(u'&', u'&amp;')
                    # elif u'<' in x[i]:
                    #    term = term.replace(u'<', u'&lt;')
                    # elif u'>' in x[i]:
                    #    term = term.replace(u'>', u'&gt;')

                    if self.config.models_pos_tag_lib == 3:
                        base = re.sub("&amp;", "&", base)
                        base = re.sub("&quot;", '"', base)
                        base = re.sub("&apos;", "'", base)
                        base = re.sub("&gt;", ">", base)
                        base = re.sub("&lt;", "<", base)
                        term = re.sub("&amp;", "&", term)
                        term = re.sub("&quot;", '"', term)
                        term = re.sub("&apos;", "'", term)
                        term = re.sub("&apos", "'", term)  # trick
                        term = re.sub("&gt;", ">", term)
                        term = re.sub("&lt;", "<", term)

                    if term in base or (swap in base if swap != '' else False):
                        index = k
                        if i == ix:
                            return index
            raise Exception

        except Exception as error:
            print error
            exit(-1)

    def __convert_sentence_to_horus_matrix(self, sentences):
        '''
        converts the list to horus_matrix
        :param sentences
        :return: horus_matrix
        '''
        self.sys.log.info(':: starting conversion to horus_matrix based on system parameters')
        converted = []
        sent_index = 0
        try:
            for sent in sentences:
                sent_index += 1
                ipositionstartterm = 0
                for c in range(len(sent[6][self.config.models_pos_tag_lib])):
                    word_index_ref = sent[6][self.config.models_pos_tag_lib][c][0]
                    compound = sent[6][self.config.models_pos_tag_lib][c][1]
                    compound_size = sent[6][self.config.models_pos_tag_lib][c][2]
                    temp = [0, sent_index, word_index_ref, compound, '', '', definitions.KLASSES[4], 1, compound_size]
                    temp.extend(self.__populate_matrix_new_columns())
                    temp.extend([definitions.KLASSES[4]])
                    converted.append(temp)
                word_index = 0
                starty = 0
                for i in range(len(sent[2][self.config.models_pos_tag_lib])):
                    term = sent[2][self.config.models_pos_tag_lib][i]
                    if len(sent[2][0]) > 0:
                        ind_ner_real = self.__get_ner_mapping_simple(sent[2][0], sent[2][self.config.models_pos_tag_lib],
                                                                   i, starty)
                        starty = ind_ner_real
                        # ind_ner = self.get_ner_mapping_slice(sent[2][0], sent[2][self.config.models_pos_tag_lib], i)
                        # ind_ner = self.get_ner_mapping2(sent[2][0], sent[2][self.config.models_pos_tag_lib], term, i)
                        is_entity = 1 if sent[3][0][ind_ner_real] in definitions.NER_TAGS else 0
                    else:
                        is_entity = -1
                    tag_ner = sent[3][self.config.models_pos_tag_lib][i] if len(
                        sent[3][self.config.models_pos_tag_lib]) > 0 else ''
                    tag_pos = sent[4][self.config.models_pos_tag_lib][i] if len(
                        sent[4][self.config.models_pos_tag_lib]) > 0 else ''
                    tag_pos_uni = sent[5][self.config.models_pos_tag_lib][i] if len(
                        sent[5][self.config.models_pos_tag_lib]) > 0 else ''
                    word_index += 1
                    # we do not know if they have the same alignment, so test it to get the correct tag
                    if len(sent[3][0]) > 0:
                        tag_ner_y = sent[3][0][ind_ner_real]
                        if tag_ner_y in definitions.NER_TAGS_LOC:
                            tag_ner_y = definitions.KLASSES[1]
                        elif tag_ner_y in definitions.NER_TAGS_ORG:
                            tag_ner_y = definitions.KLASSES[2]
                        elif tag_ner_y in definitions.NER_TAGS_PER:
                            tag_ner_y = definitions.KLASSES[3]
                        else:
                            tag_ner_y = definitions.KLASSES[4]
                    else:
                        tag_ner_y = definitions.KLASSES[4]

                    if tag_ner in definitions.NER_TAGS_LOC:
                        tag_ner = definitions.KLASSES[1]
                    elif tag_ner in definitions.NER_TAGS_ORG:
                        tag_ner = definitions.KLASSES[2]
                    elif tag_ner in definitions.NER_TAGS_PER:
                        tag_ner = definitions.KLASSES[3]
                    else:
                        tag_ner = definitions.KLASSES[4]

                    temp = [is_entity, sent_index, word_index, term, tag_pos_uni, tag_pos, tag_ner, 0, 0]  # 0-8
                    temp.extend(self.__populate_matrix_new_columns())
                    temp.extend([tag_ner_y])
                    ## that is a hack to integrate to GERBIL
                    # if ipositionstartterm >= len(sent[1][0]):
                    #    ipositionstartterm-=1
                    # if sent[1][0][ipositionstartterm] == term[0]:
                    #    if sent[1][0][ipositionstartterm:ipositionstartterm+len(term)] != term:
                    #        raise Exception("GERBIL integration: error 1!")
                    # else:
                    #    ipositionstartterm-=1
                    #    if sent[1][0][ipositionstartterm] == term[0]:
                    #        if sent[1][0][ipositionstartterm:ipositionstartterm+len(term)] != term:
                    #            raise Exception("GERBIL integration: error 2!")
                    #    else:
                    #        raise Exception("GERBIL integration: error 3!")

                    temp[27] = ipositionstartterm
                    converted.append(temp)
                    ipositionstartterm += (len(term) + 1)

        except Exception as error:
            self.sys.log.error(':: Erro! %s' % str(error))
            exit(-1)

        return converted

    def __populate_matrix_new_columns(self):
        temp = []  # receives 0=8
        temp.extend([0] * 9)  # 9-17
        temp.extend([definitions.KLASSES[4]])  # 18
        temp.extend([0] * 7)  # 19-25
        temp.extend([definitions.KLASSES[4]])  # 26
        temp.extend([0] * 9)  # 27-35
        temp.extend([definitions.KLASSES[4]] * 15)  # 36-50
        return temp

    ########################################### main ###########################################
    def annotate_text(self, text):
        """
        annotates an input text with HORUS
        :param text:
        :return:
        """
        try:
            print self.version_label
            if text is not None:
                self.sys.log.info(':: annotating text: %s' % text)
                sent_tokenize_list = self.__process_input_text(text.strip('"\''))
                self.horus_matrix = self.__convert_sentence_to_horus_matrix(sent_tokenize_list)
            else:
                raise Exception("err: missing text to be annotated")

            if len(self.horus_matrix) > 0:
                self.download_and_cache_results()
                self.detect_objects()
                self.update_compound_predictions()
                self.run_final_classifier()
                self.print_annotated_sentence()
                return self.horus_matrix

        except Exception as error:
            self.sys.log.error('sorry: ' + repr(error))

    def export_features(self, file, label=None, token_index=0, ner_index=1):
        """
        generates the training data for HORUS
        do not use the config file to choose the models, exports all features (self.detect_objects())
        :param file: a dataset (CoNLL format)
        :param label: a dataset label
        :param token_index: column index of the token (word)
        :param ner_index: column index if the target class (NER)
        :return: the feature file
        """
        try:
            print self.version_label
            if file is None:
                raise Exception("Provide an input file format to be annotated")
            self.sys.log.info(':: processing CoNLL format -> %s' % label)
            sent_tokenize_list = self.__process_ds_conll_format(file, label, token_index, ner_index, '')

            df = pd.DataFrame(sent_tokenize_list)

            self.sys.log.info(':: %s sentence(s) cached' % str(len(sent_tokenize_list)))
            tot_sentences_with_entity = len(df.loc[df[0] == 1])
            tot_others = len(df.loc[df[0] == -1])
            self.sys.log.info(':: %s sentence(s) with entity' % tot_sentences_with_entity)
            self.sys.log.info(':: %s sentence(s) without entity' % tot_others)
            self.horus_matrix = self.__convert_sentence_to_horus_matrix(sent_tokenize_list)

            hm = pd.DataFrame(self.horus_matrix)
            self.sys.log.info(':: basic POS statistics')
            a = len(hm)  # all
            a2 = len(hm[(hm[7] == 0)])  # all excluding compounds
            plo = hm[(hm[7] == 0) & (hm[0] == 1)]  # all PLO entities (not compound)
            not_plo = hm[(hm[7] == 0) & (hm[0] == 0)]  # all PLO entities (not compound)

            pos_ok_plo = plo[(plo[5].isin(definitions.POS_NOUN_TAGS))]
            pos_not_ok_plo = plo[(~plo[5].isin(definitions.POS_NOUN_TAGS))]
            pos_noun_but_not_entity = not_plo[(not_plo[5].isin(definitions.POS_NOUN_TAGS))]

            self.sys.log.info(':: [basic statistics]')
            self.sys.log.info(':: -> ALL terms: %s ' % a)
            self.sys.log.info(':: -> ALL tokens (no compounds): %s (%.2f)' % (a2, (a2 / float(a))))
            self.sys.log.info(':: -> ALL NNs (no compounds nor entities): %s ' % len(pos_noun_but_not_entity))
            self.sys.log.info(':: [test dataset statistics]')
            self.sys.log.info(':: -> PLO entities (no compounds): %s (%.2f)' % (len(plo), len(plo) / float(a2)))
            self.sys.log.info(':: -> PLO entities correctly classified as NN (POS says is NOUN): %s (%.2f)' %
                              (len(pos_ok_plo), len(pos_ok_plo) / float(len(plo)) if len(plo) != 0 else 0))
            self.sys.log.info(':: -> PLO entities misclassified (POS says is NOT NOUN): %s (%.2f)' %
                              (len(pos_not_ok_plo), len(pos_not_ok_plo) / float(len(plo)) if len(plo) != 0 else 0))

            if len(self.horus_matrix) > 0:
                self.download_and_cache_results()
                self.detect_objects()
                self.update_compound_predictions()
                outfilename = path_leaf(file) + ".horus"
                self.export_data(outfilename, "tsv")

            self.sys.log.info(':: annotation completed: ' + outfilename)
            return self.horus_matrix

        except Exception as error:
            self.sys.log.error('caught this error here: ' + repr(error))

    def get_cv_annotation(self):
        x = numpy.array(self.horus_matrix)
        return x[:, [3, 4, 12, 13, 14, 15, 16, 17]]

    def export_data(self, file, format):
        self.sys.log.info(':: exporting metadata to: ' + self.config.output_path + file + "." + format)

        if format == 'json':
            with open(self.config.output_path + file + '.json', 'wb') as outfile:
                json.dump(self.horus_matrix, outfile)
        elif format == 'csv':
            writer = csv.writer(open(self.config.output_path + file + '.csv', 'wb'), quoting=csv.QUOTE_ALL)
            writer.writerow(definitions.HORUS_MATRIX_HEADER)
            # writer.writerow([s.encode('utf8') if type(s) is unicode else s for s in self.horus_matrix])
            writer.writerows(self.horus_matrix)
        elif format == 'tsv':
            writer = csv.writer(self.config.output_path + file + '.tsv', dialect="excel", delimiter="\t", skipinitialspace=True)
            writer.writerow(definitions.HORUS_MATRIX_HEADER)
            writer.writerows(self.horus_matrix)
        else:
            raise Exception('format not implemented')



    def print_annotated_sentence(self):
        '''
        reads the components matrix and prints the annotated sentences
        :: param horus_matrix:
        :: return: output of annotated sentence
        '''
        x1, x2, x3, x4, x5 = '', '', '', '', ''
        id_sent_aux = self.horus_matrix[0][1]
        for token in self.horus_matrix:
            if token[7] == 0:
                if id_sent_aux != token[1]:
                    id_sent_aux = token[1]
                    x1 = ' ' + str(token[3]) + '/' + str(token[36])
                    x2 = ' ' + str(token[3]) + '/' + str(token[37])
                    x3 = ' ' + str(token[3]) + '/' + str(token[38])
                    x4 = ' ' + str(token[3]) + '/' + str(token[39])
                    x5 = ' ' + str(token[3]) + '/' + str(token[40])
                else:
                    x1 += ' ' + str(token[3]) + '/' + str(token[4]) + '/' + str(token[36])
                    x2 += ' ' + str(token[3]) + '/' + str(token[4]) + '/' + str(token[37])
                    x3 += ' ' + str(token[3]) + '/' + str(token[4]) + '/' + str(token[38])
                    x4 += ' ' + str(token[3]) + '/' + str(token[4]) + '/' + str(token[39])
                    x5 += ' ' + str(token[3]) + '/' + str(token[4]) + '/' + str(token[40])

        self.sys.log.info(':: sentence annotated :: ')
        self.sys.log.info(':: KLASS 1 -->: ' + x1)
        self.sys.log.info(':: KLASS 2 -->: ' + x2)
        self.sys.log.info(':: KLASS 3 -->: ' + x3)
        self.sys.log.info(':: KLASS 4 -->: ' + x4)
        self.sys.log.info(':: KLASS 5 -->: ' + x5)

    def update_database_compound(self, sentence_str, compounds):
        c = self.conn.cursor()
        col = "annotator_nltk_compounds"
        if self.config.models_pos_tag_lib == 2:
            col = "annotator_stanford_compounds"
        elif self.config.models_pos_tag_lib == 3:
            col = "annotator_tweetNLP_compounds"
        sql = """UPDATE HORUS_SENTENCES SET ? = ? WHERE sentence = ?"""
        return c.execute(sql, (col, compounds, sentence_str))

    def create_matrix_and_compounds(self, sentence_list):

        i_sent, i_word = 1, 1
        pattern = """
                NP:
                   {<JJ>*<NN|NNS|NNP|NNPS><CC>*<NN|NNS|NNP|NNPS>+}
                   {<NN|NNS|NNP|NNPS><IN>*<NN|NNS|NNP|NNPS>+}
                   {<JJ>*<NN|NNS|NNP|NNPS>+}
                   {<NN|NNP|NNS|NNPS>+}
                """
        cp = nltk.RegexpParser(pattern)
        compounds = '|'

        for sent in sentence_list:
            #  add compounds of given sentence
            aux = 0
            toparse = []

            for token in sent[2][self.config.models_pos_tag_lib]:
                toparse.append(tuple([token, sent[4][self.config.models_pos_tag_lib][aux]]))
                aux += 1
            t = cp.parse(toparse)

            i_word = 0
            for item in t:
                if type(item) is nltk.Tree:
                    is_entity = 1 if (sent[0] == 1 and sent[3][0][i_word] != 'O') else -1
                    i_word += len(item)
                    if len(item) > 1:  # that's a compound
                        compound = ''
                        for tk in item:
                            compound += tk[0] + ' '

                        self.horus_matrix.append([is_entity, i_sent, i_word - len(item),
                                                  compound[:len(compound) - 1], '', '', '', 1, len(item)])
                        compounds += compound[:len(compound) - 1] + '|'
                        compound = ''
                else:
                    i_word += 1

            # update the database with compounds for given sentence
            upd = self.update_database_compound(sent[1][0], compounds)
            #  transforming to components matrix
            # 0 = is_entity?,    1 = index_sent, 2 = index_word, 3 = word/term,
            # 4 = pos_universal, 5 = pos,        6 = ner       , 7 = compound? ,
            # 8 = compound_size
            i_word = 1
            for k in range(len(sent[2])):
                is_entity = 1 if (sent[0] == 1 and sent[3][k] != 'O') else -1
                self.horus_matrix.append(
                    [is_entity, i_sent, i_word, sent[2][k], sent[5][k], sent[4][k], sent[3][k], 0, 0])
                i_word += 1

            i_sent += 1

        # commit updates (compounds)
        self.conn.commit()

    def download_image_local(self, image_url, image_type, thumbs_url, thumbs_type, term_id, id_ner_type, seq):
        val = URLValidator()
        auxtype = None
        try:
            val(thumbs_url)
            try:
                img_data = requests.get(thumbs_url).content
                with open('%s%s_%s_%s.%s' % (self.config.cache_img_folder, term_id, id_ner_type, seq, thumbs_type),
                          'wb') as handler:
                    handler.write(img_data)
                    auxtype = thumbs_type
            except Exception as error:
                print('-> error: ' + repr(error))
        except ValidationError, e:
            self.sys.log.error('No thumbs img here...', e)
            try:
                img_data = requests.get(image_url).content
                with open('%s%s_%s_%s.%s' % (self.config.cache_img_folder, term_id, id_ner_type, seq, image_type),
                          'wb') as handler:
                    auxtype = image_type
                    handler.write(img_data)
            except Exception as error:
                print('-> error: ' + repr(error))
        return auxtype

    def download_and_cache_results(self):
        try:
            self.sys.log.info(':: caching results...')
            auxc = 1

            with SQLiteHelper(self.config.database_db) as sqlcon:
                t = HorusDB(sqlcon)
                for index in range(len(self.horus_matrix)):
                    term = self.horus_matrix[index][3]
                    if (self.horus_matrix[index][5] in definitions.POS_NOUN_TAGS) or self.horus_matrix[index][7] == 1:
                        if auxc%1000==0:
                            self.sys.log.debug(':: processing term %s - %s [%s]' % (str(auxc), str(len(self.horus_matrix)), term))
                        res = t.term_cached(term, self.config.search_engine_api, self.config.search_engine_features_text)
                        if res is None or len(res) == 0:
                            '''
                            --------------------------------------------------------------------------
                            Downloading resources...
                            --------------------------------------------------------------------------
                            '''
                            self.sys.log.info(':: not cached, querying -> [%s]' % term)

                            # Microsoft Bing
                            if int(self.config.search_engine_api) == 1:
                                metaquery, result_txts, result_imgs = query_bing(term,
                                                                                 key=self.config.search_engine_key,
                                                                                 top=self.config.search_engine_tot_resources)
                            # Flickr
                            elif (self.config.search_engine_api) == 3:
                                metaquery, result_imgs = query_flickr(term)
                                metaquery, result_txts = query_wikipedia(term)

                            '''
                            --------------------------------------------------------------------------
                            Caching Documents (Texts)
                            --------------------------------------------------------------------------
                            '''
                            self.sys.log.debug(':: caching (web sites) -> [%s]' % term)
                            id_term_search = t.save_term(term, self.config.search_engine_tot_resources,
                                                         len(result_txts), self.config.search_engine_api,
                                                         1, self.config.search_engine_features_text,
                                                         str(strftime("%Y-%m-%d %H:%M:%S", gmtime())), metaquery)
                            self.horus_matrix[index][9] = id_term_search
                            seq = 0
                            for web_result_txt in result_txts:
                                self.sys.log.info(':: caching (web site) -> [%s]' % web_result_txt['displayUrl'])
                                seq += 1
                                t.save_website_data(id_term_search, seq, web_result_txt['id'], web_result_txt['displayUrl'],
                                                    web_result_txt['name'], web_result_txt['snippet'])
                            '''
                            --------------------------------------------------------------------------
                            Caching Documents (Images)
                            --------------------------------------------------------------------------
                            '''
                            self.sys.log.info(':: caching (web images) -> [%s]' % term)
                            id_term_img = t.save_term(term, self.config.search_engine_tot_resources,
                                                      len(result_imgs), self.config.search_engine_api,
                                                      2, self.config.search_engine_features_img,
                                                      str(strftime("%Y-%m-%d %H:%M:%S", gmtime())), metaquery)
                            self.horus_matrix[index][10] = id_term_img
                            seq = 0
                            for web_result_img in result_imgs:
                                self.sys.log.debug(':: downloading image [%s]' % (web_result_img['name']))
                                seq += 1
                                auxtype = self.download_image_local(web_result_img['contentUrl'],
                                                                    web_result_img['encodingFormat'],
                                                                    web_result_img['thumbnailUrl'],
                                                                    web_result_img['encodingFormat'], id_term_img, 0,
                                                                    seq)
                                self.sys.log.debug(':: caching image  ...')
                                t.save_image_data(id_term_img, seq, web_result_img['contentUrl'],
                                                  web_result_img['name'],
                                                  web_result_img['encodingFormat'], web_result_img['height'],
                                                  web_result_img['width'], web_result_img['thumbnailUrl'], str(auxtype))

                            t.commit()
                        else:
                            if (len(res) != 2):
                                raise Exception("that should not happen!")
                            if ((1 or 2) not in [row[1] for row in res]):
                                raise Exception("that should not happen auch!")
                            self.horus_matrix[index][9] = res[0][0]
                            self.horus_matrix[index][10] = res[1][0]

                    auxc += 1

        except Exception as e:
            self.sys.log.error(':: an error has occurred: ', e)
            raise

    def remove_accents(self, data):
        return ' '.join(x for x in unicodedata.normalize('NFKD', data) if x in string.ascii_letters).lower()





    def detect_objects(self):

        # database sql
        if 1==1:
            if self.config.object_detection_type not in (0,1):
                raise Exception('parameter value not implemented: ' + str(self.config.object_detection_type))
            if self.config.text_classification_type not in (0, 1):
                raise Exception('parameter value not implemented: ' + str(self.config.text_classification_type))

        self.sys.log.info(':: detecting %s objects...' % len(self.horus_matrix))
        auxi = 0
        toti = len(self.horus_matrix)
        for index in range(len(self.horus_matrix)):
            auxi += 1
            if (self.horus_matrix[index][5] in definitions.POS_NOUN_TAGS) or self.horus_matrix[index][7] == 1:

                term = self.horus_matrix[index][3]
                self.sys.log.info(':: token %d of %d [%s]' % (auxi, toti, term))

                id_term_img = self.horus_matrix[index][10]
                id_term_txt = self.horus_matrix[index][9]
                id_ner_type = 0

                tot_geral_faces, tot_geral_logos, tot_geral_locations, tot_geral_pos_locations, \
                    tot_geral_neg_locations = 0

                tot_geral_faces_cnn, tot_geral_logos_cnn, tot_geral_locations_cnn, tot_geral_pos_locations_cnn, \
                    tot_geral_neg_locations_cnn = 0

                T = int(self.config.models_location_theta)  # location threshold

                # -----------------------------------------------------------------
                # image classification
                # -----------------------------------------------------------------

                filesimg = []
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute(SQL_OBJECT_DETECTION_SQL % (id_term_img, id_ner_type))
                    rows = cursor.fetchall()
                    nr_results_img = len(rows)
                    if nr_results_img == 0:
                        self.sys.log.debug(":: term has not returned images!")
                    limit_img = min(nr_results_img, int(self.config.search_engine_tot_resources))

                    # 0 = file path | 1 = id | 2 = processed | 3=nr_faces | 4=nr_logos | 5 to 14=nr_places_1-to-10
                    # 14 = nr_faces_cnn, 15 = nr_logos_cnn, 16-25=nr_places_1-to-10_cnn
                    for i in range(limit_img):
                        temp=[]
                        temp.append(self.config.cache_img_folder + rows[i][0])
                        temp.extend(rows[i][1:25])
                        filesimg.append(temp)

                for ifeat in filesimg:
                    if ifeat[2] == 1: # processed
                        tot_geral_faces += ifeat[3]
                        tot_geral_logos += ifeat[4]
                        tot_geral_faces_cnn += ifeat[14]
                        tot_geral_logos_cnn += ifeat[15]
                        if (ifeat[5:14]).count(1) >= int(T):
                            tot_geral_locations += 1
                        if (ifeat[16:25]).count(1) >= int(T):
                            tot_geral_locations_cnn += 1
                        tot_geral_pos_locations += ifeat[5:14].count(1)
                        tot_geral_neg_locations += (ifeat[5:14].count(-1) * -1)
                        tot_geral_pos_locations_cnn += ifeat[16:25].count(1)
                        tot_geral_neg_locations_cnn += (ifeat[16:25].count(-1) * -1)

                    else:
                        if self.config.object_detection_type in (-1,0):
                            # ----- face recognition -----
                            tot_faces = self.detect_faces(ifeat[0])
                            if tot_faces > 0:
                                tot_geral_faces += 1
                                self.sys.log.debug(":: found {0} faces!".format(tot_faces))
                            # ----- logo recognition -----
                            tot_logos = self.detect_logo(ifeat[0])
                            if tot_logos[0] == 1:
                                tot_geral_logos += 1
                                self.sys.log.debug(":: found {0} logo(s)!".format(1))
                            # ----- place recognition -----
                            res = self.detect_place(ifeat[0])
                            tot_geral_pos_locations += res.count(1)
                            tot_geral_neg_locations += (res.count(-1) * -1)

                            if res.count(1) >= T:
                                tot_geral_locations += 1
                                self.sys.log.debug(":: found {0} place(s)!".format(1))

                        elif self.config.object_detection_type in (-1,1):
                            image = self.cnn.preprocess_image(ifeat[0])
                            # ----- face recognition -----
                            tot_faces = self.cnn.detect_faces(image)
                            if tot_faces > 0:
                                tot_geral_faces_cnn += 1
                                self.sys.log.debug(":: found {0} faces!".format(tot_faces))
                            # ----- logo recognition -----
                            tot_logos = self.detect_logo_cnn(image)
                            if tot_logos[0] == 1:
                                tot_geral_logos_cnn += 1
                                self.sys.log.debug(":: found {0} logo(s)!".format(1))
                            # ----- place recognition -----
                            res = self.detect_place_cnn(image)
                            tot_geral_pos_locations_cnn += res.count(1)
                            tot_geral_neg_locations_cnn += (res.count(0) * -1)

                            if res.count(1) >= T:
                                tot_geral_locations_cnn += 1
                                self.sys.log.debug(":: found {0} place(s)!".format(1))

                        # updating results
                        if self.config.object_detection_type == 0:  # SIFT
                            _sql = sql_object_0_upd
                        elif self.config.object_detection_type == 1:  # CNN
                            _sql = sql_object_1_upd
                        elif self.config.object_detection_type == -1: #ALL
                            _sql = sql_object_upd
                        else:
                            raise Exception('parameter value not implemented: ' + str(self.config.object_detection_type))

                        param = []
                        param.append(tot_faces)
                        param.append(tot_logos[0]) if tot_logos[0] == 1 else param.append(0)
                        param.extend(res)
                        param.append(ifeat[1])
                        cursor.execute(sql_object_upd, param)

                self.conn.commit()

                outs = [tot_geral_locations, tot_geral_logos, tot_geral_faces]
                maxs_cv = heapq.nlargest(2, outs)
                dist_cv_indicator = max(maxs_cv) - min(maxs_cv)
                place_cv_indicator = tot_geral_pos_locations + tot_geral_neg_locations

                self.horus_matrix[index][11] = limit_img
                self.horus_matrix[index][12] = tot_geral_locations  # 1
                self.horus_matrix[index][13] = tot_geral_logos  # 2
                self.horus_matrix[index][14] = tot_geral_faces  # 3
                self.horus_matrix[index][15] = dist_cv_indicator  # 4
                self.horus_matrix[index][16] = place_cv_indicator  # 5
                self.horus_matrix[index][17] = nr_results_img  # 5

                self.sys.log.debug(':: CV statistics:'
                                   '(LOC=%s, ORG=%s, PER=%s, DIST=%s, PLC=%s)' %
                                   (str(tot_geral_locations).zfill(2), str(tot_geral_logos).zfill(2),
                                    str(tot_geral_faces).zfill(2), str(dist_cv_indicator).zfill(2), place_cv_indicator))

                if limit_img != 0:
                    self.horus_matrix[index][18] = definitions.KLASSES[outs.index(max(outs)) + 1]
                else:
                    self.horus_matrix[index][18] = definitions.KLASSES[4]

                # -----------------------------------------------------------------
                # text classification
                # -----------------------------------------------------------------
                y = []
                with self.conn:
                    cursor = self.conn.cursor()
                    if self.config.text_classification_type == 0:  # SIFT
                        _sql = sql_text_0_sel
                    elif self.config.text_classification_type == 1:  # CNN
                        _sql = sql_text_1_sel

                    cursor.execute(_sql % (id_term_txt, id_ner_type))
                    rows = cursor.fetchall()

                    nr_results_txt = len(rows)
                    if nr_results_txt == 0:
                        self.sys.log.debug(":: term has not returned web sites!")
                    limit_txt = min(nr_results_txt, int(self.config.search_engine_tot_resources))

                    tot_err = 0
                    for itxt in range(limit_txt):

                        if rows[itxt][6] == 0 or rows[itxt][6] is None:  # not processed yet

                            if self.config.text_classification_type == 0:
                                ret = self.detect_text_klass(rows[itxt][2], rows[itxt][3], rows[itxt][0], rows[itxt][4], rows[itxt][5])
                                _sql = sql_text_0_upd
                            elif self.config.text_classification_type == 1:
                                ret = self.detect_text_klass(rows[itxt][2], rows[itxt][3], rows[itxt][0], rows[itxt][4], rows[itxt][5])
                                _sql = sql_text_1_upd

                            y.append(ret)
                            sql = _sql % (ret[0], ret[1], ret[2], ret[3], ret[4], rows[itxt][0])
                            cursor.execute(sql)
                            if ret[0] == -1 or ret[1] == -1 or ret[2] == -1 or ret[3] == -1 or ret[4] == -1:
                                tot_err += 1
                        else:
                            y.append(rows[itxt][7:12])

                    self.conn.commit()

                    yy = numpy.array(y)
                    gp = [numpy.count_nonzero(yy == 1), numpy.count_nonzero(yy == 2), numpy.count_nonzero(yy == 3)]
                    horus_tx_ner = gp.index(max(gp)) + 1

                    self.horus_matrix[index][19] = limit_txt
                    self.horus_matrix[index][20] = gp[0]
                    self.horus_matrix[index][21] = gp[1]
                    self.horus_matrix[index][22] = gp[2]
                    self.horus_matrix[index][23] = float(tot_err)

                    maxs_tx = heapq.nlargest(2, gp)
                    dist_tx_indicator = max(maxs_tx) - min(maxs_tx)

                    self.horus_matrix[index][24] = dist_tx_indicator
                    self.horus_matrix[index][25] = nr_results_txt

                    self.sys.log.debug(':: TX statistics:'
                                       '(LOC=%s, ORG=%s, PER=%s, DIST=%s, ERR.TRANS=%s)' %
                                       (str(gp[0]).zfill(2), str(gp[1]).zfill(2), str(gp[2]).zfill(2),
                                        str(dist_tx_indicator).zfill(2),
                                        str(tot_err / float(limit_txt)) if limit_txt > 0 else 0))
                    self.sys.log.debug('-------------------------------------------------------------')

                    if limit_txt != 0:
                        self.horus_matrix[index][26] = definitions.KLASSES[horus_tx_ner]
                    else:
                        self.horus_matrix[index][26] = definitions.KLASSES[4]

                    # checking final NER based on:
                    #  -> theta
                    if self.horus_matrix[index][15] >= int(self.config.models_distance_theta):
                        self.horus_matrix[index][36] = self.horus_matrix[index][18]  # CV is the final decision
                        self.horus_matrix[index][39] = self.horus_matrix[index][36]  # compound prediction initial
                    elif self.horus_matrix[index][24] >= int(self.config.models_distance_theta):
                        self.horus_matrix[index][36] = self.horus_matrix[index][26]  # TX is the final decision
                        self.horus_matrix[index][39] = self.horus_matrix[index][36]  # compound prediction initial
                    #  -> theta+1
                    if self.horus_matrix[index][15] >= int(self.config.models_distance_theta) + 1:
                        self.horus_matrix[index][37] = self.horus_matrix[index][18]  # CV is the final decision
                    elif self.horus_matrix[index][24] >= int(self.config.models_distance_theta) + 1:
                        self.horus_matrix[index][37] = self.horus_matrix[index][26]  # TX is the final decision
                    #  -> theta+2
                    if self.horus_matrix[index][15] >= int(self.config.models_distance_theta) + 2:
                        self.horus_matrix[index][38] = self.horus_matrix[index][18]  # CV is the final decision
                    elif self.horus_matrix[index][24] >= int(self.config.models_distance_theta) + 2:
                        self.horus_matrix[index][38] = self.horus_matrix[index][26]  # TX is the final decision

    def update_rules_cv_predictions(self):
        '''
        updates the predictions based on inner rules
        :return:
        '''
        self.sys.log.info(':: updating predictions based on rules')
        for i in range(len(self.horus_matrix)):
            initial = self.horus_matrix[i][17]
            # get nouns or compounds
            if self.horus_matrix[i][4] == 'NOUN' or \
                    self.horus_matrix[i][4] == 'PROPN' or self.horus_matrix[i][7] == 1:
                # do not consider classifications below a theta
                if self.horus_matrix[i][15] < int(self.config.models_distance_theta):
                    self.horus_matrix[i][17] = "*"
                # ignore LOC classes having iPLC negative
                if bool(int(self.config.models_distance_theta_high_bias)) is True:
                    if initial == "LOC":
                        if self.horus_matrix[i][16] < int(self.config.models_limit_min_loc):
                            self.horus_matrix[i][17] = "*"
                        elif self.horus_matrix[i][16] < 0 and self.horus_matrix[i][15] > \
                                int(self.config.models_safe_interval):
                            self.horus_matrix[i][17] = initial

    def update_compound_predictions(self):
        '''
        pre-requisite: the matrix should start with the sentence compounds at the beginning.
        '''
        self.sys.log.info(':: updating compounds predictions')
        i_y, i_sent, i_first_word, i_c_size = [], [], [], []
        for i in range(len(self.horus_matrix)):
            if self.horus_matrix[i][7] == 1:
                i_y.append(self.horus_matrix[i][36])  # KLASS_1
                i_sent.append(self.horus_matrix[i][1])
                i_first_word.append(self.horus_matrix[i][2])
                i_c_size.append(int(self.horus_matrix[i][8]))
            if self.horus_matrix[i][7] == 0:
                for z in range(len(i_y)):
                    if i_sent[z] == self.horus_matrix[i][1] and i_first_word[z] == self.horus_matrix[i][2]:
                        for k in range(i_c_size[z]):
                            self.horus_matrix[i + k][39] = i_y[z]  # KLASS_4




    # ########################################### temp ###########################################

    def __cache_sentence_ritter(self, sentence_list):
        self.sys.log.debug(':: caching Ritter dataset...:')
        i_sent, i_word = 1, 1
        compound, prev_tag = '', ''
        sent_with_ner = 0
        token_ok = 0
        compound_ok = 0
        for sent in sentence_list:

            self.sys.log.info(':: processing sentence: ' + sent[1])
            if int(sent[1])==29:
                aaa=1

            # processing compounds
            if sent[0] == 1:
                sent_with_ner += 1
                for tag in sent[3]:  # list of NER tags
                    word = sent[2][i_word - 1]
                    if tag in definitions.NER_RITTER:  # only desired tags
                        if prev_tag.replace('B-', '').replace('I-', '') == tag.replace('B-', '').replace('I-', ''):
                            compound += prev_word + ' ' + word + ' '
                    prev_word = word
                    prev_tag = tag
                    i_word += 1
                compound = compound[:-1]

                if compound != '':
                    compound_ok += 1
                    self.horus_matrix.append([1, i_sent, i_word - len(compound.split(' ')), compound, '', '', '', 1,
                                              len(compound.split(' '))])
                    compound = ''
                prev_tag = ''
                prev_word = ''

            # processing tokens

            #  transforming to components matrix
            # 0 = is_entity?,    1 = index_sent, 2 = index_word, 3 = word/term,
            # 4 = pos_universal, 5 = pos,        6 = ner       , 7 = compound? ,
            # 8 = compound_size

            i_word = 1
            for k in range(len(sent[2])):  # list of NER tags
                is_entity = 1 if sent[3] in definitions.NER_RITTER else 0
                self.horus_matrix.append(
                    [is_entity, i_sent, i_word, sent[2][k], sent[5][k], sent[4][k], sent[3][k], 0, 0])
                i_word += 1
                if is_entity:
                    token_ok += 1

            i_sent += 1
            i_word = 1

        self.sys.log.debug(':: done! total of sentences = %s, tokens = %s and compounds = %s'
                           % (str(sent_with_ner), str(token_ok), str(compound_ok)))

    def __cache_sentence_conll(self, sentence_list):
        self.sys.log.debug(':: caching coNLL 2003 dataset...:')
        i_sent, i_word = 1, 1
        compound, prev_tag = '', ''
        sent_with_ner = 0
        token_ok = 0
        compound_ok = 0
        for sent in sentence_list:

            self.sys.log.info(':: processing sentence: ' + sent[1])
            if int(sent[1])==29:
                aaa=1

            # processing compounds
            if sent[0] == 1:
                sent_with_ner += 1
                for chunck_tag in sent[6]:  # list of chunck tags
                    word = sent[2][i_word - 1]
                    if chunck_tag in "I-NP":  # only NP chunck
                        if prev_tag.replace('I-NP', 'NP').replace('B-NP', 'NP') == chunck_tag.replace('I-NP',
                                                                                                      'NP').replace(
                                'B-NP', 'NP'):
                            if compound == "":
                                compound += prev_word + ' ' + word + ' '
                            else:
                                compound += word + ' '
                    elif compound != "":
                        prev_tag = ''
                        prev_word = ''
                        compound_ok += 1
                        compound = compound[:-1]
                        self.horus_matrix.append([1, i_sent, i_word - len(compound.split(' ')), compound, '', '', '', 1,
                                                  len(compound.split(' '))])
                        compound = ''
                    prev_word = word
                    prev_tag = chunck_tag
                    i_word += 1
                compound = compound[:-1]

                if compound != '':
                    compound_ok += 1
                    self.horus_matrix.append([1, i_sent, i_word - len(compound.split(' ')), compound, '', '', '', 1,
                                              len(compound.split(' '))])
                    compound = ''
                prev_tag = ''
                prev_word = ''

            # processing tokens

            #  transforming to components matrix
            # 0 = is_entity?,    1 = index_sent, 2 = index_word, 3 = word/term,
            # 4 = pos_universal, 5 = pos,        6 = ner       , 7 = compound? ,
            # 8 = compound_size

            i_word = 1
            for k in range(len(sent[2])):  # list of NER tags
                is_entity = 1 if sent[3] in definitions.NER_CONLL else 0

                self.horus_matrix.append(
                    [is_entity, i_sent, i_word, sent[2][k], sent[5][k], sent[4][k], sent[3][k], 0, 0])
                i_word += 1
                if is_entity:
                    token_ok += 1

            self.__db_save_sentence(sent[1], '-', '-', str(sent[3]))
            i_sent += 1
            i_word = 1

        self.sys.log.debug(':: done! total of sentences = %s, tokens = %s and compounds = %s'
                           % (str(sent_with_ner), str(token_ok), str(compound_ok)))

    def __cache_sentence(self, sentence_format, sentence_list):
        if sentence_format == 1:
            self.__cache_sentence_ritter(sentence_list)
        elif sentence_format == 2:
            self.__cache_sentence_conll(sentence_list)

    def __deletar_depois(self):
        try:
            c = self.conn.cursor()
            c2 = self.conn.cursor()
            self.conn.text_factory = str
            sql = """SELECT id, annotator_nltk_compounds, annotator_stanford_compounds, annotator_tweetNLP_compounds
                     FROM HORUS_SENTENCES"""
            c.execute(sql)
            res = c.fetchall()
            if not res is None:
                for reg in res:
                    id = reg[0]
                    u0 = json.loads(reg[1])
                    u1 = json.loads(reg[2])
                    u2 = json.loads(reg[3])
                    for item in u0:
                        item[0] = int(item[0]) + 1
                    for item in u1:
                        item[0] = int(item[0]) + 1
                    for item in u2:
                        item[0] = int(item[0]) + 1
                    sql = """UPDATE HORUS_SENTENCES SET annotator_nltk_compounds = ?,
                              annotator_stanford_compounds = ?, annotator_tweetNLP_compounds = ?
                            WHERE id = ?"""
                    c2.execute(sql, (json.dumps(u0), json.dumps(u1), json.dumps(u2), id))
            # self.conn.commit() -> ja fiz o que tinha que fazer...
        except Exception as e:
            print e
            self.conn.rollback()

    def __db_save_sentence(self, sent, corpus):
        try:
            c = self.conn.cursor()
            self.conn.text_factory = str
            sentence = [corpus, sent[0], sent[1][0], sent[1][1], sent[1][2], sent[1][3],
                        json.dumps(sent[2][0]), json.dumps(sent[2][1]), json.dumps(sent[2][2]), json.dumps(sent[2][3]),
                        json.dumps(sent[3][0]), json.dumps(sent[3][1]), json.dumps(sent[3][2]), json.dumps(sent[3][3]),
                        json.dumps(sent[4][0]), json.dumps(sent[4][1]), json.dumps(sent[4][2]), json.dumps(sent[4][3]),
                        json.dumps(sent[5][0]), json.dumps(sent[5][1]), json.dumps(sent[5][2]), json.dumps(sent[5][3]),
                        json.dumps(sent[6][1]), json.dumps(sent[6][2]), json.dumps(sent[6][3])]
            id = c.execute(sql_save_sentence, sentence)
            self.conn.commit()
            return id.lastrowid

        except Exception as e:
            self.sys.log.error(':: an error has occurred: ', e)
            raise