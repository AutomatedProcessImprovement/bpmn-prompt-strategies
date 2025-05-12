# Thesis Prompting Framework

This repository contains code and structure supporting the thesis work on prompting methods and evaluation benchmark for BPMN-based process understanding.

## 📁 File Overview

There are four main Python files, each implementing a different prompting method:

- `raw.py` 
- `simplified.py`
- `humanified.py`
- `dfg.py`
  
Each of these files accepts a **BPMN model path** as input in the `main()` function. They either:
- Print the generated prompt structure, or
- Insert the generated prompt into the appropriate **process dictionary** for use in the pipeline.

## 🗂 File Structure

├── models/

│ ├── <complexity_level>/

│ │ ├── <process_name>/

│ │ │ ├── model.bpmn

│ │ │ ├── questions.json

│ │ │ └── prompts/

│ │ │ ├── raw.txt

│ │ │ ├── simplified.txt

│ │ │ ├── humanified.txt

│ │ │ └── dfg.txt

- **`models/`**: Stores **complexity-level folders**, each containing **process dictionaries**.
- Each process dictionary includes:
  - A BPMN model file (`model.bpmn`)
  - Associated evaluation questions (`questions.json`)
  - A `prompts/` folder for storing generated `.txt` prompt files from each method.

> ✅ You can add as many complexity levels and processes as needed.

## 🚀 Evaluation Pipeline

The main evaluation flow is defined in:

- `pipeline_main.py`

This file iterates through the models and evaluates the prompts using an LLM, as proposed in the thesis.

### 🔧 Setup

1. **API Key Setup**  
   On **line 129** of `pipeline_main.py`, set your API key:
   ```python
   OPENAI_API_KEY = "<YOUR API KEY>"

2. **LLM Initialization**  
   On **line 19**, set up your model (adjust for your LLM provider and model name):
   ```python
   llm = ChatOpenAI(model="<YOUR MODEL>", temperature=0, openai_api_key=api_key)

3. **File Structure**  
   Ensure your `models/` folder is correctly structured and populated as shown above.

## ▶️ Run the Pipeline
  ```python
  python pipeline_main.py
