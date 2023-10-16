__author__ = "Oren Halvani"
__copyright__ = "Copyright 2023, Oren Halvani, Derivation of *** Corpus of German-Language Fiction ***"
__license__ = "Apache 2.0"
__version__ = "1.0.0"
__maintainer__ = "Oren Halvani"
__status__ = "Production"


import os
import re 
import shutil
from pathlib import Path
from enum import Enum
import operator as Operator
from tqdm.auto import tqdm
from pprint import pprint
import torch
import spacy


class FileSizeOrder(Enum):
    Unordered = 1
    Ascending = 2
    Descending = 3


def list_subdirectories(base_path):
    ''' Lists all sub directories for a given base directory. '''
    sub_dirs = [f.path for f in os.scandir(base_path) if f.is_dir()]
    return sub_dirs  
    
    
    
def keep_n_files_in_each_subfolder(dir_path, 
                                   number_of_files_to_keep, 
                                   extension=".txt", 
                                   file_size_order=FileSizeOrder.Descending, 
                                   verbose=False):
    """Given an AA corpus, keep n files in each subfolder (author-directory) and remove the rest.
    file_size_order=FileSizeOrder.Decending --> Big files first..
    """

    affected_files_to_kill = []
    subdirs = list_subdirectories(dir_path)
    for subdir in tqdm(subdirs):
        # Apply desired file size order.
        known_filepaths = list_filepaths_with_sizes(subdir, extension=extension, order=file_size_order)

        # Select only the filepaths.
        known_filepaths = [filepath for filepath, _ in known_filepaths]

        # Choose number of files to keep.
        kill_filepaths = known_filepaths[number_of_files_to_keep:]
        affected_files_to_kill.extend(kill_filepaths)

        # Remove remaining files in the sub directory.
        for kill_filepath in kill_filepaths:
            os.remove(kill_filepath)

    if verbose:
        print(f'Deletion completed! {len(affected_files_to_kill)} affected files: \n-------------------------------------------------------')
        pprint(affected_files_to_kill)


        
def list_filepaths_with_sizes(dir_path, order=FileSizeOrder.Descending, extension=".txt", include_subdirs=True):
    temp = list_filepaths(dir_path, extension=extension, include_subdirs=include_subdirs)
    filepaths = [(filepath, os.stat(filepath).st_size) for filepath in temp]

    if order == FileSizeOrder.Ascending:
        return sorted(filepaths, key=Operator.itemgetter(1), reverse=False)
    elif order == FileSizeOrder.Descending:
        return sorted(filepaths, key=Operator.itemgetter(1), reverse=True)
    return filepaths        
        
        

def list_filepaths(base_path, extension=".txt", include_subdirs=False, list_only_empty_files=False):
    ''' Lists all files for a given base directory. '''
    filepaths = []
    if include_subdirs:
        for filepath, include_subdirs, files in os.walk(base_path):
            for name in files:
                filepaths.append(os.path.join(filepath, name))
    else:
        for file in os.listdir(base_path):
            filepaths.append(os.path.join(base_path, file))

    # filter by extension
    filepaths = [filepath for filepath in filepaths if os.path.basename(filepath).endswith(extension)]

    # filter by null size
    if list_only_empty_files:
        filepaths = [filepath for filepath in filepaths if os.stat(filepath).st_size == 0]

    return filepaths
    
    
def move_file(filepath, dest_folder):
    new_filepath = Path(dest_folder, Path(filepath).name)
    shutil.move(filepath, new_filepath)
    return Path(new_filepath).exists()


def delete_subdirs_with_operator_n_files(dir_path, 
                                         minimum_number_of_files, 
                                         operator, 
                                         extension=".txt", 
                                         verbose=False):
    ''' Intention: Given an AA corpus, keep n files in each subfolder (author-directory)
    if Operator.X applies and KILL the rest. Here, X stands for the respective operator e.g., = as 'eq' WITHOUT ().'''
    subdirs = list_subdirectories(dir_path)
    affected_directories = []

    for subdir in tqdm(subdirs):
        filepaths = list_filepaths(subdir, extension)
        if operator(len(filepaths), minimum_number_of_files):
            # if verbose:
            #     print(f'{len(filepaths)} {operator} {minimum_number_of_files} --> {operator(len(filepaths), minimum_number_of_files)}')
            affected_directories.append(subdir)
            shutil.rmtree(subdir)

    if verbose:
        pprint(affected_directories, width=pprint_width)
        print()
        print(f'Deleted: {len(affected_directories)} directories.')