# Project Environment Setup Guide

This guide outlines the steps to initialize, manage, and replicate the Python development environment for the **QC_PCB** project.

## 1. Initial Environment Setup
Run these commands once to create your local isolated environment.

**Install virtualenv tool:**
\`\`\`Command Prompt
py -m pip install virtualenv
\`\`\`

**Create the virtual environment:**
\`\`\`Command Prompt
py -m venv pcb_env
\`\`\`

**Activate the virtual environment:**
\`\`\`Command Prompt
pcb_env\Scripts\activate
\`\`\`
> **Note:** Once activated, you should see \`(pcb_env)\` appearing at the start of your terminal line.

## 2. Installing Dependencies
After activation, install the core AI libraries required for the project.

**Install the Ultralytics framework (for YOLOv11):**
\`\`\`Command Prompt
py -m pip install ultralytics
\`\`\`

**Install all dependencies from the requirements file:**
\`\`\`Command Prompt
pip install -r requirements.txt
\`\`\`

## 3. Managing Packages
Use these commands to verify your setup or share your environment with team members.

**List all installed packages:**
\`\`\`Command Prompt
pip list
\`\`\`

**Export the current environment to a file:**
\`\`\`Command Prompt
pip freeze > requirements.txt
\`\`\`
*This creates a snapshot of your environment for other developers to replicate your setup.*

## 4. Maintenance & Cross-Device Development
**Deactivate the virtual environment:**
\`\`\`Command Prompt
deactivate
\`\`\`

**Install development-specific packages on a new device:**
\`\`\`Command Prompt
pip install -r requirements-dev.txt
\`\`\`

---
**Warning:** Do not upload the \`pcb_env/\` folder to GitHub. Ensure it is listed in your \`.gitignore\` file.


/// phan moi them vao 
py -m pip install pyqt6-tools
py -m pip install pyqt6
C:\Users\NguyenDucBinh\AppData\Local\Programs\Python\Python310\Lib\site-packages\pyqt6_plugins\Qt\bin\designer.exe

py -m PyQt6.uic.pyuic -o ui_main.py ui_main.ui
.\pcb_env\Scripts\python.exe main.py
.\pcb_env\Scripts\python.exe -m PyQt6.uic.pyuic -o ui_main.py ui_main.ui
.\pcb_env\Scripts\python.exe -m pip install watchdog

