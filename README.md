#### HORUS Framework: Boosting NER

[![HitCount](http://hits.dwyl.io/SmartDataAnalytics/horus-ner.svg)](http://hits.dwyl.io/SmartDataAnalytics/horus-ner)
[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/SmartDataAnalytics/horus-ner/issues)

<!--[![NSP Status](https://nodesecurity.io/orgs/sda/projects/4fe69258-6d3c-40d0-9ed6-fc4b3b183466/badge)](https://nodesecurity.io/orgs/sda/projects/4fe69258-6d3c-40d0-9ed6-fc4b3b183466)-->
<!--[![Build Status](https://travis-ci.org/SmartDataAnalytics/horus-ner.svg?branch=master)](https://travis-ci.org/SmartDataAnalytics/horus-ner)-->
<!--[![bitHound Overall Score](https://www.bithound.io/github/SmartDataAnalytics/horus-ner/badges/score.svg)](https://www.bithound.io/github/SmartDataAnalytics/horus-ner) -->
<!--[![bitHound Code](https://www.bithound.io/github/SmartDataAnalytics/horus-ner/badges/code.svg)](https://www.bithound.io/github/SmartDataAnalytics/horus-ner)-->
<!--[![Coverage Status](https://coveralls.io/repos/SmartDataAnalytics/horus-ner/badge.svg?branch=master&service=github)](https://coveralls.io/github/SmartDataAnalytics/horus-ner?branch=master)-->
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/SmartDataAnalytics/horus-ner/graphs/commit-activity)
[![GitHub license](https://img.shields.io/github/license/SmartDataAnalytics/horus-ner.svg)](https://github.com/SmartDataAnalytics/horus-ner/blob/master/LICENSE)

HORUS is a Named Entity Recognition (NER) Framework specifically
designed for short-text, e.g.: social media, websites, blogs and etc..

It provides a set of computer vision and text mining features 
at word-level to boost the task on noisy data.

We are currently investigating Named Entity Recognition (NER) as use case. This version supports the identification of classical named-entity types (LOC, PER, ORG). 

#### Easy Setup (Python 2.7 based)

1. Run the bash script
- bash scripts/setup_horus.sh

1. Setup the python environment
- setup [Anaconda](https://anaconda.org/)
- conda env create -f horus.v015.yml (tested for OSX) (*)
- source activate horus_27_cv310

2. Setup the framework environment
- setup [SQLite](https://sqlite.org/) database and run [our script](https://github.com/diegoesteves/horus-ner/blob/master/horus0.1.5.db.sql) to create the schema
- get your [Microsoft Bing API Key](https://azure.microsoft.com/en-us/services/cognitive-services/) and [Microsoft Translator API Key](https://datamarket.azure.com/developer/applications/register) to query the Web.
- configure the parameters at the .ini file (copy _horus_dist.ini_ to _~/horus.ini_)

(*) - setup [openCV 3.1](http://www.pyimagesearch.com/2015/06/22/install-opencv-3-0-and-python-2-7-on-ubuntu/): OSx users can benefit from anaconda, which provides a running version of OpenCV 3.1.0 ([see more at #issue 6](https://github.com/dnes85/horus-models/issues/6))

#### Demo
[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)

```python
python main.py --text="whitney houston has been honored in nyc"

python main.py --file="sentences.txt" --ds_format=0

python main.py --file="ritter_ner.tsv" --ds_format=1 --output_file="metadata" --output_format="json"
```

#### Experiments

```python
# X = conll file
# 1. caching webpages and images (cache.py)
X2 = cache_se_results_conll(X)

# 2. extracting horus features (features.py)
X3 = extract_features_from_conll(X2, output_folder, label)

# 3. adding lexical features and benchmarking
y = benchmark(X3)

```

##### 
```python

```

#### Web Service
```python
export FLASK_APP=rest.py
user$ flask run

browser:
http://localhost:5000/annotate?text=paris hilton
```

#### pip (soon :-))
```python
pip install horus

import horus
config = HorusConfig()
sentence = "paris hilton was once the toast of the town"
extractor = FeatureExtraction(config, load_sift=1, load_tfidf=1, load_cnn=0, load_topic_modeling=1)
print(extractor.extract_features_text(sentence))
```
#### Changelog
- 0.1.0 initial version
- 0.1.1 adding text classification
- 0.1.2 adding map detection
- 0.1.5
    - text-classification enhancements
    - bug-fix
- 0.2.0
    - web service
    - topic modeling
