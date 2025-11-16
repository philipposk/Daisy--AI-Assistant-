# Installing PyAudio for Full Voice Support

## The Issue

PyAudio requires the PortAudio system library to be installed first. If you see errors about `portaudio.h` not found, you need to install PortAudio.

## Solution (macOS)

### Option 1: Using Homebrew (Recommended)

```bash
# Install PortAudio system library
brew install portaudio

# Then install pyaudio
pip install pyaudio
```

### Option 2: Using Conda (If using Anaconda/Miniconda)

```bash
# Install portaudio and pyaudio via conda
conda install -c conda-forge portaudio
conda install -c conda-forge pyaudio
```

### Option 3: Skip PyAudio (Voice input will still work)

Daisy can work without PyAudio! Speech recognition will use alternative methods.

Just run:
```bash
python3 agent-controller/daisy-assistant.py
```

Or for text mode:
```bash
python3 agent-controller/daisy-assistant.py --text
```

## Quick Fix for Your Current Issue

Since you're using conda, run:

```bash
conda install -c conda-forge portaudio pyaudio
```

Then try running Daisy again:
```bash
python3 agent-controller/daisy-assistant.py
```

## Verify Installation

Test if pyaudio works:
```bash
python3 -c "import pyaudio; print('✅ PyAudio installed successfully')"
```

