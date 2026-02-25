# fibirr-GUI
**February 25<sup>th</sup>, 2026**

GUI for fibirr setup based on AvaSpec library

## Installation
Python 3.12 or higher is required

### Conda
The Anaconda Powershell Prompt is a good tool.
#### 1) Create a new Python environment and install pip
```bash
(base) conda create -n fibirr-GUI
(base) conda activate fibirr-GUI
(fibirr-GUI) conda install pip
```

#### 2) Download the source files
##### Clone using URL at desired location (for example, Desktop):
```bash
(fibirr-GUI) conda install git
(fibirr-GUI) cd Desktop
(fibirr-GUI) \Desktop> git clone https://github.com/CrespiLab/fibirr-GUI.git
```
A folder called "fibirr-GUI" is downloaded.

#### 3) Add AvaSpec library
- Inside `fibirr-GUI` directory, create a directory called `avantes`
- Place DLL inside `avantes` directory (e.g., avaspecx64.dll)

#### 4) Install
```bash
(fibirr-GUI) \Desktop> cd fibirr-GUI
(fibirr-GUI) \Desktop\fibirr-GUI> pip install -e .
```

## Run
Make sure to activate the environment, and then call the .pyw file using Python:

```
(base) conda activate fibirr-GUI
(fibirr-GUI) \Desktop\fibirr-GUI> python GUI.pyw
```
The GUI should appear after a short while.

(*command-line script coming soon*)

### Configuration
The user can adjust the desired default settings in the `settings.py` file that is located in the folder `user`.
