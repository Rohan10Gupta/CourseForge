#%% Importing Libraries
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 19 19:58:08 2024

@author: Rohan
"""

import docx2txt
import re
import pickle
#Changes heading 2 to heading 3, adds bullet points where needed, returns formatted text
def format_text(text):
  formatted_text = ""
  for line in text.splitlines():
    if line.startswith("###"):
      formatted_text += f"\n##{line[3:]}\n"
    elif line.startswith("* "):
      formatted_text += f"- {line[2:]}\n"
    elif line.startswith("**"):
        formatted_text += f"\n- {line[:]}\n"
    else:
      formatted_text += f"{line}\n"
  print("Text Formatted")
  return formatted_text

def format_outlines_notion(text):
  formatted_text = ""
  for line in text.splitlines():
    if line.startswith("###"):
      formatted_text += f"\n##{line[4:]}\n"
    elif line.startswith("* "):
      formatted_text += f"- {line[2:]}\n"
    elif line.startswith("- **Objective:**") or line.startswith("- **Key Topics:**") or line.startswith("- **Activities:**"):
        formatted_text += f"\n{line[2:]}\n"
    else:
      formatted_text += f"{line}\n"
  return formatted_text

def format_outline(text):
    formatted_text = ""
    for line in text.splitlines():
        if line.startswith("####"):
            formatted_text += f"\n{line[5:]}\n"
        elif line.startswith("##  "):
            formatted_text += f"\n{line[3:]}\n"        
        elif line.startswith("###"):
            formatted_text += f"\n{line[4:]}\n"
        elif line.startswith("* "):
            formatted_text += f"{line[2:]}\n"
        elif line.startswith("**Module"):
            formatted_text += f"\n{line[2:-2]}\n"
        else:
            formatted_text += f"{line}\n"
    return formatted_text

def format_outlines(text):
    formatted_text = ""
    i = 0
    j = 0
    for line in text.splitlines():
        if line.startswith("####"):
            i = 0
            formatted_text += f"\n{line}\n"
        elif line.startswith("**"):
            i += 1
            j = 0
            formatted_text += f"\n**Chapter {i}: {line[3:]}\n"
        elif line.startswith("   -"):
            j += 1
            formatted_text += f"\n{i}.{j}: {line[5:]}\n"
        else:
          formatted_text += f"{line}\n"
    return formatted_text

def create_outline_dict(outline):
    outline_dict = {}
    module_dict = {}
    for line in outline.splitlines():
        if line.startswith("Course Title"):
            course_title = line
        elif line.startswith("Module"):
            module_title = line
        elif line.startswith("---"):
            continue
        elif line == "":
            continue
        else:
            if module_title in module_dict.keys():
                module_dict[module_title] += f"\n{line}"
            else:
                module_dict[module_title] = line
    outline_dict[course_title] = module_dict
    return outline_dict

def unpack_outlines(gemini_outlines):
    outlines = {}
    for course_title, module in gemini_outlines.items():
        for module_title, module_summary in module.items():
            module_summary = format_outlines_notion(module_summary)
            m = {}
            text = ""
            i = 0
            j = 0
            flag = 0
            for line in module_summary.splitlines():
                if line.startswith("## Module"):
                    if line.endswith(" "):
                        page_title = f"{line[3:-1]}"
                    else:
                        page_title = f"{line[3:]}"
                    flag = 6
                elif line.startswith("##Overview"):
                    text += f"## {line[2:]}\n"
                elif line.startswith("##Chapter"):
                    i += 1
                    j = 0
                    m[page_title] = text
                    text = ""
                    # Strip existing numbering to avoid doubling
                    raw_title = line[9:]  # after "##Chapter"
                    title_part = re.sub(r'^\s*\d+\s*:\s*', '', raw_title)
                    page_title = f"Chapter {i}: {title_part}"
                    flag = 2
                elif line.startswith("##"):
                    j += 1
                    m[page_title] = text
                    text = ""
                    # Strip existing numbering to avoid doubling
                    raw_title = line[2:]
                    title_part = re.sub(r'^\d+(\.\d+)?\s*:\s*', '', raw_title)
                    page_title = f"{i}.{j}: {title_part}"
                    flag = 2
                else:
                    if flag == 0:
                        text += f"{line}\n"
                    else:
                        flag -= 1
            m[page_title] = text
            outlines[module_title] = m
    return outlines

def remove_spaces(text, flag):
    formatted_text = ""
    for line in text.splitlines():
        if line.startswith("---"):
            formatted_text += f"{line}\n"
        elif line == "":
            formatted_text += f"\n"
        else:
            formatted_text += re.sub(r'\s+', ' ', line)
            if flag == 0:
                formatted_text += '\n'
    return formatted_text    

def introduction_reformat(course_introduction, course_title):
    print("Formatting Introduction")
    text = course_introduction
    introduction = {}
    for line in text.splitlines():
        if (line.startswith('Module') or course_title[19:] in line):
            if course_title[19:] in line:
                module_title = course_title
            else:
                module_title = line
        elif line.startswith("---"):
            continue
        else:
            if module_title in introduction.keys():
                introduction[module_title] += f"\n{line}"
            else:
                introduction[module_title] = line
    print("Introduction Reformatted")
    return introduction
#%%
# content = docx2txt.process('Sample Text.docx')
#%%
# =============================================================================
# with open('Module Summaries.pkl', 'rb') as f:  # open a text file
#     gemini_module_summaries_raw = pickle.load(f) # serialize the list
# f.close()
# =============================================================================
#%%
    
    
    
    
    
    