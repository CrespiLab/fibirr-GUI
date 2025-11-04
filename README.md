# fibirr-GUI
GUI for fibirr setup based on AvaSpec library

## Installation
Python 3.12 or higher is required

### Conda
The Anaconda Powershell Prompt is a good tool.
#### Create a new Python environment and install pip
```bash
(base) conda create -n fibirr-GUI
(base) conda activate fibirr-GUI
(fibirr-GUI) conda install pip
```

#### Download the source files
##### Clone using URL at desired location (for example, Desktop):
```bash
(fibirr-GUI) conda install git
(fibirr-GUI) cd Desktop
(fibirr-GUI) \Desktop> git clone https://github.com/CrespiLab/fibirr-GUI.git
```
A folder called "fibirr-GUI" is downloaded.

#### Add AvaSpec library

#### Install
```bash
(fibirr-GUI) \Desktop> cd fibirr-GUI
(fibirr-GUI) \Desktop\fibirr-GUI> pip install -e .
```

## Run
Make sure to activate the environment, and then call the .pyw file using Python:
(working on command-line script)
```
(base) conda activate fibirr-GUI
(fibirr-GUI) \Desktop\fibirr-GUI> python GUI.pyw
```
The GUI should appear after a short while.

### Configuration
The user can adjust the desired default settings in the `settings.py` file that is located in the folder `user`.
