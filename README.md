# Text-to-Speech Tool

A modular GUI application for text-to-speech synthesis using PyQt5, supporting multiple TTS engines.

## Features

- **Multiple TTS Engines**: Support for Edge TTS and custom engines
- **Automatic SRT Generation**: Every synthesis creates both MP3 and SRT files with synchronized timing
- **Intelligent Sentence Splitting**: Smart text segmentation for accurate subtitle timing
- **Podcast Creator**: Multi-speaker dialogue support with automatic voice assignment
- **Modular Design**: Easy to add new TTS engines
- **Language & Voice Selection**: Choose from multiple languages and voices
- **Voice Settings**: Adjust rate and volume
- **Organized File Export**: Automatic timestamped folders with MP3 and SRT files
- **Threaded Synthesis**: Non-blocking UI during synthesis

## Requirements

- Python 3.7+
- PyQt5
- For Edge TTS: `pip install edge-tts`

## Installation

1. Install Python dependencies:
```bash
pip install PyQt5
pip install edge-tts  # For Edge TTS engine
```

2. Clone or download this repository

3. Run the application:
```bash
python main.py
```

## Configuration

The `config.json` file contains all engine configurations:

- **engines**: Configuration for each TTS engine
  - **edge-tts**: Microsoft Edge TTS settings
  - **custom**: Template for custom TTS engines

## Adding Custom TTS Engines

1. Create a new engine class inheriting from `TTSEngine` in the `engines/` directory
2. Implement the required abstract methods:
   - `synthesize()`: Convert text to audio
   - `get_available_voices()`: Return list of voices
   - `get_available_languages()`: Return list of languages
   - `is_available()`: Check if dependencies are installed

3. Add your engine configuration to `config.json`

4. Update `engines/__init__.py` to import your new engine

5. Update the GUI to instantiate your engine

## Project Structure

```
toolTTS/
├── main.py                 # Application entry point
├── gui.py                  # Main GUI application
├── config.json            # Configuration file
├── engines/               # TTS engine modules
│   ├── __init__.py
│   ├── base_engine.py     # Abstract base class with SRT generation
│   ├── edge_engine.py     # Edge TTS implementation
│   └── custom_engine.py   # Custom engine template
└── README.md             # This file
```

## Usage

1. Select a TTS engine from the dropdown
2. Choose language and voice
3. Adjust rate and volume if desired
4. Enter text to synthesize
5. Click "Synthesize" to generate audio
6. Save the audio file or play it (playback not implemented in demo)

## Extending the Application

### Adding New Voices/Languages

Edit `config.json` to add new languages and voices for existing engines.

### Adding New Engines

1. Implement your engine class
2. Add configuration to `config.json`
3. Update the GUI to load your engine

### Custom Engine Template

Use `engines/custom_engine.py` as a starting point for implementing your own TTS engine. Replace the placeholder code with your actual TTS implementation.

## SRT Subtitle Generation

All TTS engines automatically generate SRT subtitle files alongside MP3 audio:

1. **Intelligent sentence splitting** using punctuation detection (. ! ?)
2. **Proper abbreviation handling** (Mr., Dr., etc. don't break sentences)
3. **Accurate timing calculation** based on text length and speech rate
4. **Standard SRT format** compatible with all video players
5. **Automatic file organization** in timestamped folders

### Example Output Structure:
```
20251201_143052/
├── 20251201_143052.mp3  # Synthesized audio
└── 20251201_143052.srt  # Synchronized subtitles
```

### SRT File Format:
```
1
00:00:00,000 --> 00:00:02,500
Hello world. This is the first sentence.

2
00:00:02,600 --> 00:00:05,200
How are you doing today?
```

## Podcast Creator

Create multi-speaker podcasts with automatic voice assignment and synchronized audio:

### Features:
- **Multi-Speaker Support**: Write dialogue with speaker labels
- **Automatic Speaker Detection**: Parse speakers from script format
- **Language & Voice Selection**: Choose language and default voice for podcast
- **Voice Assignment**: Assign different voices to each speaker
- **Individual Settings**: Customize rate and volume per speaker
- **Combined Output**: Single MP3 + SRT file for the full podcast

### Script Format:
```
Host: Welcome to our podcast!
Guest: Thanks for having me.
Host: Tell us about your project.
Guest: It's going really well!
```

### Podcast SRT Format:
```
1
00:00:00,000 --> 00:00:02,500
[Host]: Welcome to our podcast!

2
00:00:02,600 --> 00:00:05,100
[Guest]: Thanks for having me.
```

## Troubleshooting

### Edge TTS Issues

**"edge-tts is not installed"**
- Install edge-tts: `pip install edge-tts`

### General Issues

**GUI not starting**
- Install PyQt5: `pip install PyQt5`
- On Linux: `apt-get install python3-pyqt5` (or equivalent)

**Audio not saving**
- Check write permissions in the current directory
- The `audio_out/` directory will be created automatically

## License

This project is provided as-is for educational and development purposes.
