__author__ = "Oren Halvani"
__copyright__ = "Copyright 2023, Oren Halvani, Derivation of *** Corpus of German-Language Fiction ***"
__license__ = "Apache 2.0"
__version__ = "1.0.0"
__maintainer__ = "Oren Halvani"
__status__ = "Production"


import os
import re
import torch
import spacy
import shutil
import requests
from pathlib import Path
from enum import Enum
import operator as Operator
from tqdm.auto import tqdm
from pprint import pprint
from . import os_utils

nlp = spacy.load("de_core_news_lg")


def download_file(url, dest_filename):
    response = requests.get(url)
    if response.status_code == 200:
        with open(dest_filename,'wb') as f:
            f.write(response.content) 
            
    if Path(dest_filename).exists():
        print(f"Download successful. File has been written to:\n{dest_filename}")
    else:
        print(response.raise_for_status())


def get_author_name(filepath):
    author_name = Path(filepath).name
    author_name = author_name[0:author_name.find("_-_")].strip()
    return author_name


def create_aa_corpus(base_path):
    filepaths = os_utils.list_filepaths(base_path)
    
    for filepath in tqdm(filepaths):    
        author_name = get_author_name(filepath)
        dest_path = Path(base_path, author_name)

        if os.path.exists(dest_path):
            os_utils.move_file(filepath, str(dest_path))
        else:
            dest_path.mkdir() 
            os_utils.move_file(filepath, str(dest_path))
            
            
def extract_paragraphs(path, threshold_min_tokens_per_paragraph=30):
    text = Path(path).read_text(encoding="utf8")
    pattern = "[\n]{2,}[a-zäöüßA-ZÄÖÜ0-9 \n,.;:!?'–-]+[\n]{2,}"

    paragraphs = re.findall(pattern, text)
    paragraphs = [p.strip() for p in paragraphs]
    paragraphs = [p[p.find("\n\n"):].strip() for p in paragraphs if "\n\n" in p]
    paragraphs = [p for p in paragraphs if len(p.split()) > threshold_min_tokens_per_paragraph]
    paragraphs = [" ".join(p.splitlines()) for p in paragraphs] 
    
    return paragraphs


def extract_sentences(paragraphs):
    sentences = []
    for paragarph in paragraphs:
        par_sents = nlp(paragarph).sents
        par_sents = [s.text.strip() for s in par_sents if not s.text.endswith(":")]
        sentences.extend(par_sents)
        
    return sentences


def concatenate_sentences_up_to_n_chars(sentences, max_total_chars=7000):
    cnt = 0
    sentences_2_take = []
    for sentence in sentences:
        cnt = cnt + len(sentence)
        if cnt <= max_total_chars:
            sentences_2_take.append(sentence)

    return " ".join(sentences_2_take)


def preprocess_sentences(sentences):
    cleaned_sentences = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        sentence_tokens = sentence.split()
        
        # Skip sentences that...
        # ----------------------------------------------------------------------
        # contain [Cc]opyright mentions (e.g.,  "opyright ")
        if "opyright" in sentence:
            continue
            
        # consist of single tokens (e.g., '1858.', '1.', ..)
        if len(sentence_tokens) <= 1:
            continue
            
        # solely consist of title case tokens (e.g., 'Carl Rümpler.', 'Eine Häuerfamilie.', 'Titelblatt  I.', etc.)
        if all([tok.istitle() == True for tok in sentence_tokens]):
            continue
        
        # contain too many (>= 3) hyphens "–" (e.g., 'Eine Häuerfamilie – Ein Sohn – Pater Joseph – Forsthaus und..')
        if len(re.findall("[–-]+", sentence)) > 3:
            continue
        
        # contain chapter headers (e.g., 'Kapitel[.:]')
        if len(re.findall("Kapitel[.:]+", sentence)) > 0:
            continue
            
        # have no valid sentence terminators (e.g., 'Im Avalun-Verlag Hellerau bei Dresden     ')
        if not (sentence.endswith(".") or 
                sentence.endswith("!") or 
                sentence.endswith("?") or 
                sentence.endswith(":") or
                sentence.endswith(";")):
            continue
        
        # contain many multiple consecutive spaces.
        if len(re.findall("\s{2,}", sentence)) >= 3:
            continue
        # ----------------------------------------------------------------------
        
        # Replace sentences..
        # ----------------------------------------------------------------------
        # containing ". . ." with "..." and " ..." with "..."
        sentence = sentence.replace(". . .", "...").replace(" ...", "...")
                    
        #  that start with hyphens      
        sentence = re.sub("^[–-]+\s*", "", sentence)
        
        # that contain multiple consecutive spaces. 
        sentence = re.sub("\s{2,}", " ", sentence)
        # ----------------------------------------------------------------------
        
        cleaned_sentences.append(sentence)
    return cleaned_sentences
  
    
def construct_documents(filepaths, max_total_chars=7000):
    for filepath in tqdm(filepaths):
        paragraphs = extract_paragraphs(filepath) 
        sentences = extract_sentences(paragraphs)
        cleaned_sentences = preprocess_sentences(sentences)
        concat_text = concatenate_sentences_up_to_n_chars(cleaned_sentences, max_total_chars=max_total_chars)
        Path(filepath).write_text(concat_text, encoding="utf8")
        
        
def delete_files_according_to_length(base_path, min_length=1000, extension=".txt", verbose=False):
    filepaths = os_utils.list_filepaths_with_sizes(base_path, order=os_utils.FileSizeOrder.Descending, extension=".txt", include_subdirs=True)
    deleted_files = []
    
    for filepath, text_len in filepaths:
        if text_len < min_length:
            deleted_files.append(filepath)
            os.remove(filepath)
         
    if verbose:    
        for deleted_file in deleted_files:
            print(deleted_file)
        print(f'Deleted: {len(deleted_files)} files.')
        
         
def maximize_time_span_and_remove_inner_documents(base_path):
    """Given a path to an aa corpus, choose for each author those documents for which the time span is maximum. Remaining documents will be deleted! """

    authors = os_utils.list_subdirectories(base_path)

    for author in tqdm(authors):
        filepaths_per_author = os_utils.list_filepaths(author)
        
        sorted_filepaths_per_author = sorted(filepaths_per_author, key=lambda f: (int(re.findall("\(([0-9]{4})\)", Path(f).name)[-1]), -Path(f).stat().st_size))
        for middle_path in sorted_filepaths_per_author[1:-1]:
            Path(middle_path).unlink()