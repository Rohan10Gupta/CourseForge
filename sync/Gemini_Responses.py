#%% Importing Libraries
import pickle
import time
import requests as req
# import google.generativeai as genai
# from google.api_core.exceptions import DeadlineExceeded
# from google.generativeai.types import HarmCategory, HarmBlockThreshold
import docx2txt
from Markdown_Function import format_text, format_outline
import os
from dotenv import load_dotenv
load_dotenv()

# --- Backend toggle: set to "ollama" or "gemini" ---
USE_BACKEND = "ollama"

# Ollama config
# OLLAMA_MODEL = "ikiru/Dolphin-Mistral-24B-Venice-Edition:latest"
OLLAMA_MODEL = "llama3.2:3b" #For testing purposes
OLLAMA_URL = "http://localhost:11434/api/generate"

print(f"Using backend: {USE_BACKEND} | Model: {OLLAMA_MODEL if USE_BACKEND == 'ollama' else 'gemini-2.0-flash-lite'}")
# Gemini config (kept for easy switch back)
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
if USE_BACKEND == "gemini":
    import google.generativeai as genai
    from google.api_core.exceptions import DeadlineExceeded
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash-lite')

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), 'checkpoints')

def _save_checkpoint(data, flag):
    """Save intermediate results after each generation."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    filename = 'module_summaries_partial.pkl' if flag == 1 else 'chapter_content_partial.pkl'
    filepath = os.path.join(CHECKPOINT_DIR, filename)
    with open(filepath, 'wb') as f:
        pickle.dump(data, f)

class _OllamaResponse:
    """Wrapper to match Gemini's response.text interface."""
    def __init__(self, text):
        self.text = text

def _generate_with_retry(prompt, safety_settings, module_title):
    """Call the active backend with retry on failure."""
    for attempt in range(1, 4):
        try:
            if USE_BACKEND == "ollama":
                resp = req.post(OLLAMA_URL, json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False
                }, timeout=300)
                resp.raise_for_status()
                return _OllamaResponse(resp.json()["response"])
            else:
                return model.generate_content(prompt, safety_settings=safety_settings)
        except Exception as e:
            if attempt < 3:
                print(f"Error on {module_title}, retrying ({attempt}/3)...")
                time.sleep(10)
            else:
                raise

#Check Available Gemini Models
# =============================================================================
# for m in genai.list_models():
#   if 'generateContent' in m.supported_generation_methods:
#     print(m.name)
# =============================================================================

#%% Functions
#Pass the outlines to gemini, and record the output in a dict.
# flag == 1 :- Outline to Module Summary
# flag == 0 :- Module outline to Chapter Summary
def gemini_output(course_outline, flag, existing_results=None):
    gemini_outlines = existing_results if existing_results else {}
    safety_settings = None
    if USE_BACKEND == "gemini":
        safety_settings = {
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    i = 1
    for course_title, module in course_outline.items():
        g = gemini_outlines.get(course_title, {})
        response = 1
        for module_title, module_content in module.items():
            if module_title in g:
                label = module_title[:9] if "Chapter" in module_title else module_title[:8]
                print(f"---\nPrompt {i}, {label} Skipping (cached)")
                i += 1
                continue
            if flag == 1:
                prompt_skele = docx2txt.process('Docs/Course Outline Prompt Skeleton.docx')
                prompt = f"{prompt_skele} \n{course_title} \n{module_title} \n{module_content}"
            elif flag == 0:
                prompt_skele = docx2txt.process('Docs/Chapter Prompt Skeleton.docx')
                instructor_introduction = docx2txt.process('Docs/Instructor Introduction File.docx')
                prompt = f"{instructor_introduction} {course_title} {prompt_skele} {module_content}"
            if "Chapter" in module_title:
                print(f"---\nPrompt {i}, {module_title[:9]} Generating")
            else:
                print(f"---\nPrompt {i}, {module_title[:8]} Generating")
            response = _generate_with_retry(prompt, safety_settings, module_title)
            response_text = ""
            try:
                response_text = response.text
            except ValueError as ve:
                print(response.candidates)
                print("Reseting Prompting")
                reset_flag = 0
            response_text = format_text(response_text)
            g[module_title] = response_text
            gemini_outlines[course_title] = g
            _save_checkpoint(gemini_outlines, flag)
            if "Chapter" in module_title:
                print(f"Prompt {i}, {module_title[:9]} Success")
            else:
                print(f"Prompt {i}, {module_title[:3]} Success")
            i += 1
        gemini_outlines[course_title] = g
        reset_flag = 1
    return gemini_outlines, response, reset_flag

def gemini_outlines(course_subject):
    student_intro = docx2txt.process('Docs/Student Introduction File.docx')
    prompt_skele = docx2txt.process('Docs/Outlines Prompt Skeleton.docx')
    #course_subject = "Astrophysics"
    prompt = f"Create a course outline with this overview: {course_subject}.\n\nThis is the introduction of the student you will be building the course for:\n{student_intro}\n------\n\n{prompt_skele}"
    print(f"Generating Outline.")
    safety_settings = None
    if USE_BACKEND == "gemini":
        safety_settings = {HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE}
    response = _generate_with_retry(
        prompt,
        safety_settings,
        "Course Outline"
    )
    response_text = response.text
    response_text = format_outline(response_text)
    print("Outline Generated")
    return response_text, response

def gemini_introduction(outline_raw):
    prompt_skele = docx2txt.process('Docs/Course Introduction Skeleton.docx')
    prompt = f"{prompt_skele}\n{outline_raw}"
    print("Generating Introduction")
    safety_settings = None
    if USE_BACKEND == "gemini":
        safety_settings = {
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    response = _generate_with_retry(
        prompt,
        safety_settings,
        "Course Introduction"
    )
    response_text = response.text
    response_text = format_outline(response_text)
    print("Introduction Generated")
    return response_text
#%%
if __name__ == "__main__":
#%%
    with open('Course Outline.pkl', 'rb') as f:
        course_outline = pickle.load(f) # deserialize using load()
    f.close()
    gemini_module_summaries, reponse = gemini_output(course_outline, 1)
    with open('Gemini Module Summaries.pkl', 'wb') as f:  # open a text file
        pickle.dump(gemini_module_summaries, f) # serialize the list
    f.close()
    #%% Grab outlines from pickle file (Notion update takes Gemini Module Summaries and formats them to make pickle file)
    with open('Module Summaries Dict.pkl', 'rb') as f:
        outlines = pickle.load(f) # deserialize using load()
    f.close()
    gemini_content, response = gemini_output(outlines, 0)
    with open('Animation Course.pkl', 'wb') as f:  # open a text file
        pickle.dump(gemini_content, f) # serialize the list
    f.close()
#%%










