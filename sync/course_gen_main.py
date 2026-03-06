import os
import sys
import pickle
import time

from dotenv import load_dotenv
load_dotenv()

#%% -*- coding: utf-8 -*-
"""
Created on Thu Aug  8 00:57:01 2024

@author: Rohan
"""
#%%
import requests
import docx2txt


from Gemini_Responses import gemini_output, gemini_outlines, gemini_introduction
from Notion_Update import (
    create_top_page, course_introduction_to_notion,
    course_outlines_to_notion, outline_reformat,
    page_to_notion, get_children_pages
)
from Markdown_Function import  create_outline_dict, remove_spaces, introduction_reformat

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), 'checkpoints')

def load_checkpoint(name):
    """Load a checkpoint file if it exists."""
    filepath = os.path.join(CHECKPOINT_DIR, name)
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        print(f"Loaded checkpoint: {name}")
        return data
    return None

def save_checkpoint(data, name):
    """Save a checkpoint file."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    filepath = os.path.join(CHECKPOINT_DIR, name)
    with open(filepath, 'wb') as f:
        pickle.dump(data, f)
    print(f"Saved checkpoint: {name}")

def clear_checkpoints():
    """Remove all checkpoint files."""
    if os.path.exists(CHECKPOINT_DIR):
        for f in os.listdir(CHECKPOINT_DIR):
            os.remove(os.path.join(CHECKPOINT_DIR, f))
        print("Checkpoints cleared")

def clean_double_spaces_course(gemini_module_summaries_raw):
    gemini_module_summaries = {}
    g = {}
    for course_title, course in gemini_module_summaries_raw.items():
        for module_title, module_summary in course.items():
            mod = remove_spaces(module_title, 1)
            summary = remove_spaces(module_summary, 0)
            g[mod] = summary
    gemini_module_summaries[course_title] = g
    return gemini_module_summaries

def clean_double_spaces_intro(gemini_module_summaries_raw):
    g = {}
    for module_title, module_summary in gemini_module_summaries_raw.items():
        mod = remove_spaces(module_title, 1)
        summary = remove_spaces(module_summary, 0)
        g[mod] = summary
    return g

def create_course_outline(subject):
    # Stage 1: Outline
    cached = load_checkpoint('outline.pkl')
    if cached:
        outline_raw, course_outline = cached
    else:
        outline_raw, response = gemini_outlines(subject)
        print("Outine Generated")
        course_outline = create_outline_dict(outline_raw)
        print("Outine Dictionary Created")
        save_checkpoint((outline_raw, course_outline), 'outline.pkl')

    # Stage 2: Introduction
    cached = load_checkpoint('intro.pkl')
    if cached:
        course_introduction = cached
    else:
        course_introduction_raw = gemini_introduction(outline_raw)
        print("Course Intro Generated")
        for course_title in course_outline.keys(): pass
        course_introduction_ds = introduction_reformat(course_introduction_raw, course_title)
        course_introduction = clean_double_spaces_intro(course_introduction_ds)
        save_checkpoint(course_introduction, 'intro.pkl')

    # Create a new page in the Courses Main Page for the new course
    for course_title in course_outline.keys(): course_page_id = create_top_page(course_title[14:])
    # Add introduction and module pages to the course page
    course_introduction_to_notion(course_introduction, course_page_id)
    print("Main Page Created")

    # Stage 3: Module summaries
    cached = load_checkpoint('module_summaries.pkl')
    if cached:
        gemini_module_summaries = cached
    else:
        existing_summaries = load_checkpoint('module_summaries_partial.pkl')
        gemini_module_summaries_raw, reponse, reset_flag = gemini_output(course_outline, 1, existing_results=existing_summaries)
        gemini_module_summaries = clean_double_spaces_course(gemini_module_summaries_raw)
        save_checkpoint(gemini_module_summaries, 'module_summaries.pkl')
    print("Module Summaries Generated")

    # Create headings, subheadings, and add the course outlines to the headings
    course_outlines_to_notion(gemini_module_summaries, course_page_id, course_introduction)
    print("Module Pages Created")
    return gemini_module_summaries, course_page_id

def create_course(gemini_module_summaries, course_page_id):
    # Reformat the module summaries to fit the format needed for gemini input
    module_summaries = outline_reformat(gemini_module_summaries)
    print("Outline Reformated")
    # Load partial chapter results if they exist
    existing_chapters = load_checkpoint('chapter_content_partial.pkl')
    # Generate course from moudule summaries
    reset_flag = 0
    while reset_flag == 0:
        gemini_content, response, reset_flag = gemini_output(module_summaries, 0, existing_results=existing_chapters)
    save_checkpoint(gemini_content, 'chapter_content.pkl')
    print("Chapters Generated")
    # Add chapter pages directly to course
    page_to_notion(gemini_content, course_page_id)
    print("Chapter Pages Created")
    return 0

#%%
if '--fresh' in sys.argv:
    clear_checkpoints()
    print("Starting fresh run")

start_time = time.time()
# subject = input("1.Please describe the subject that you would like B.O.B to teach you. Include any specific topics, modules or key words you'd like to focus on. Remember, the more detailed your answer, the better B.O.B can help you! ")
subject = docx2txt.process('Docs/Subject.docx')

gemini_module_summaries, course_page_id = create_course_outline(subject)
create_course(gemini_module_summaries, course_page_id)

print("Course Created")
print("--- %s minutes ---" % ((time.time() - start_time)/60))

def test():
    #%%
    # subject = "How do I learn build a game similar to Zombie Estate on the Raspberry Pie 5?"
    #%%
    subject = docx2txt.process('Docs/Subject.docx')
    # Generate a course outline from the subject provided by user
    outline_raw, response = gemini_outlines(subject)
    print("Outine Generated")
    # Generate course introduction with the outline
    course_introduction_raw = gemini_introduction(outline_raw)
    print("Course Intro Generated")
    # Create a dict from the raw outline in the format needed for input to Gemini
    course_outline = create_outline_dict(outline_raw)
    print("Outine Dictionary Created")
    # Create a new page in the Courses Main Page for the new course
    for course_title in course_outline.keys(): course_page_id = create_top_page(course_title[14:])
    # Add introduction and module pages to the course page
    #%%
    course_introduction_ds = introduction_reformat(course_introduction_raw, course_title)
    course_introduction = clean_double_spaces_intro(course_introduction_ds)
    #%%
    course_introduction_to_notion(course_introduction, course_page_id)
    print("Main Page Created")
    #%%
    # Generate module summaries from the outline
    gemini_module_summaries_raw, reponse, reset_flag = gemini_output(course_outline, 1)
    gemini_module_summaries = clean_double_spaces_course(gemini_module_summaries_raw)
    print("Module Summaries Generated")
    #%%
    # Create heaadings, subheadings, and add the course outlines to the headings
    course_outlines_to_notion(gemini_module_summaries, course_page_id, course_introduction)
    print("Module Pages Created")
    #%%
    # Reformat the module summaries to fit the format needed for gemini input
    module_summaries = outline_reformat(gemini_module_summaries)
    print("Outline Reformated")
    # Generate course from moudule summaries
    reset_flag = 0
    while reset_flag == 0:
        gemini_content, response, reset_flag = gemini_output(module_summaries, 0)
    print("Chapters Generated")
    # Add chapter pages directly to course
    page_to_notion(gemini_content, course_page_id)
    print("Chapter Pages Created")
    #%%
    with open('Course Intro.pkl', 'rb') as f:  # open a text file
        course_introduction_raw = pickle.load(f) # serialize the list
    f.close()
    #%%
    with open('Course Intro.pkl', 'wb') as f:
        pickle.dump(course_introduction_raw, f)
    f.close()
    return 0
#%%
