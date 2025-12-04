"""
Main GUI application for Text-to-Speech Tool
"""
import sys
import json
import os
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QComboBox, QPushButton, QProgressBar,
    QGroupBox, QFormLayout, QSlider, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon

from engines import EdgeTTSEngine, CustomTTSEngine


class TTSThread(QThread):
    """Thread for TTS synthesis to avoid blocking the UI"""
    finished = pyqtSignal(bytes, str)  # Now returns both audio and SRT
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    cancelled = pyqtSignal()

    def __init__(self, engine, text: str, voice_id: str, **kwargs):
        super().__init__()
        self.engine = engine
        self.text = text
        self.voice_id = voice_id
        self.kwargs = kwargs
        self._cancelled = False

    def run(self):
        """Run TTS synthesis in background thread"""
        try:
            self.progress.emit(10)
            if self._cancelled:
                self.cancelled.emit()
                return

            # Use synthesize_with_subtitles to get both audio and SRT
            audio_data, srt_content = self.engine.synthesize_with_subtitles(self.text, self.voice_id, **self.kwargs)

            if self._cancelled:
                self.cancelled.emit()
                return

            self.progress.emit(100)
            self.finished.emit(audio_data, srt_content)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))

    def cancel(self):
        """Cancel the synthesis"""
        self._cancelled = True


class TTSApp(QMainWindow):
    """Main TTS Application Window"""

    def __init__(self):
        super().__init__()
        self.current_language = 'en'  # Default language
        self.translations = self.load_language_file()
        self.config = self.load_config()
        self.engines = {}
        self.current_engine = None
        self.audio_data = None

        self.init_engines()
        self.init_ui()
        self.load_default_settings()
        self.update_ui_text()  # Apply initial language

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            error_msg = self.get_text("messages.error_config_not_found", "config.json file not found!")
            QMessageBox.critical(self, "Error", error_msg)
            sys.exit(1)
        except json.JSONDecodeError as e:
            error_msg = self.get_text("messages.error_invalid_config", f"Invalid config.json: {str(e)}").format(error=str(e))
            QMessageBox.critical(self, "Error", error_msg)
            sys.exit(1)

    def load_language_file(self) -> Dict[str, Any]:
        """Load language translations from ui_language.json"""
        lang_path = os.path.join(os.path.dirname(__file__), 'ui_language.json')
        try:
            with open(lang_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return default English if file not found
            return {
                "en": {
                    "window_title": "Text-to-Speech Tool",
                    "tts_engine": "TTS Engine",
                    "engine": "Engine:",
                    "language_voice": "Language & Voice",
                    "language": "Language:",
                    "voice": "Voice:",
                    "voice_settings": "Voice Settings",
                    "rate": "Rate:",
                    "volume": "Volume:",
                    "text_to_synthesize": "Text to Synthesize",
                    "text_placeholder": "Enter text here...",
                    "synthesize": "Synthesize",
                    "cancel": "Cancel",
                    "save_audio": "Save Audio",
                    "ready": "Ready",
                    "synthesizing": "Synthesizing...",
                    "synthesis_completed": "Synthesis completed!",
                    "synthesis_failed": "Synthesis failed!",
                    "cancelling_synthesis": "Cancelling synthesis...",
                    "synthesis_cancelled": "Synthesis cancelled",
                    "change_language": "Change Language",
                    "messages": {}
                },
                "vi": {}
            }
        except json.JSONDecodeError:
            # Return default English if JSON is invalid
            return {"en": {}, "vi": {}}

    def get_text(self, key: str, default: str = "") -> str:
        """Get translated text for a given key"""
        lang_dict = self.translations.get(self.current_language, {})
        if key.startswith("messages."):
            # Handle nested messages
            parts = key.split(".")
            value = lang_dict
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, {})
                else:
                    return default
            return value if isinstance(value, str) else default
        return lang_dict.get(key, default)

    def init_engines(self):
        """Initialize TTS engines"""
        engine_configs = self.config.get('engines', {})

        if 'edge-tts' in engine_configs:
            self.engines['edge-tts'] = EdgeTTSEngine(engine_configs['edge-tts'])

        if 'custom' in engine_configs:
            self.engines['custom'] = CustomTTSEngine(engine_configs['custom'])

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Text-to-Speech Tool")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)

        # Language switcher button (top right)
        lang_button_layout = QHBoxLayout()
        lang_button_layout.addStretch()
        self.lang_switch_btn = QPushButton("Change Language")
        self.lang_switch_btn.clicked.connect(self.on_language_switch)
        lang_button_layout.addWidget(self.lang_switch_btn)
        layout.addLayout(lang_button_layout)

        # Engine selection
        engine_group = QGroupBox("TTS Engine")
        self.engine_group = engine_group  # Store reference for translation
        engine_layout = QHBoxLayout(engine_group)

        self.engine_combo = QComboBox()
        for engine_id, engine in self.engines.items():
            if engine.is_available():
                self.engine_combo.addItem(engine.name, engine_id)
            else:
                self.engine_combo.addItem(f"{engine.name} (Not Available)", engine_id)

        self.engine_combo.currentIndexChanged.connect(self.on_engine_changed)
        self.engine_label = QLabel("Engine:")
        engine_layout.addWidget(self.engine_label)
        engine_layout.addWidget(self.engine_combo)

        layout.addWidget(engine_group)

        # Language and Voice selection
        selection_group = QGroupBox("Language & Voice")
        self.selection_group = selection_group  # Store reference for translation
        selection_layout = QHBoxLayout(selection_group)

        self.language_combo = QComboBox()
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)

        self.voice_combo = QComboBox()

        self.language_label = QLabel("Language:")
        selection_layout.addWidget(self.language_label)
        selection_layout.addWidget(self.language_combo)
        self.voice_label = QLabel("Voice:")
        selection_layout.addWidget(self.voice_label)
        selection_layout.addWidget(self.voice_combo)

        layout.addWidget(selection_group)

        # Voice settings
        settings_group = QGroupBox("Voice Settings")
        self.settings_group = settings_group  # Store reference for translation
        settings_layout = QFormLayout(settings_group)

        # Rate slider
        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setRange(-50, 50)
        self.rate_slider.setValue(0)
        self.rate_slider.setTickInterval(10)
        self.rate_slider.setTickPosition(QSlider.TicksBelow)
        self.rate_label = QLabel("+0%")
        self.rate_slider.valueChanged.connect(self.on_rate_changed)

        # Volume slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(-50, 50)
        self.volume_slider.setValue(0)
        self.volume_slider.setTickInterval(10)
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        self.volume_label = QLabel("+0%")
        self.volume_slider.valueChanged.connect(self.on_volume_changed)

        self.rate_label_text = QLabel("Rate:")
        settings_layout.addRow(self.rate_label_text, self.rate_slider)
        settings_layout.addRow("", self.rate_label)
        self.volume_label_text = QLabel("Volume:")
        settings_layout.addRow(self.volume_label_text, self.volume_slider)
        settings_layout.addRow("", self.volume_label)

        layout.addWidget(settings_group)

        # Text input
        text_group = QGroupBox("Text to Synthesize")
        self.text_group = text_group  # Store reference for translation
        text_layout = QVBoxLayout(text_group)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Enter text here...")
        text_layout.addWidget(self.text_edit)

        layout.addWidget(text_group)

        # Control buttons
        button_layout = QHBoxLayout()

        self.synthesize_btn = QPushButton("Synthesize")
        self.synthesize_btn.clicked.connect(self.on_synthesize)
        self.synthesize_btn.setEnabled(False)

        self.save_btn = QPushButton("Save Audio")
        self.save_btn.clicked.connect(self.on_save_audio)
        self.save_btn.setEnabled(False)
        self.save_btn.setVisible(False)  # Hide save button, auto-save enabled

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.on_cancel_synthesize)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setVisible(False)

        button_layout.addWidget(self.synthesize_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        # Initialize with first engine
        if self.engine_combo.count() > 0:
            self.on_engine_changed(0)

        # Connect text changed signal
        self.text_edit.textChanged.connect(self.on_text_changed)

    def on_language_switch(self):
        """Handle language switch button click"""
        # Toggle between English and Vietnamese
        self.current_language = 'vi' if self.current_language == 'en' else 'en'
        self.update_ui_text()

    def update_ui_text(self):
        """Update all UI text based on current language"""
        # Window title
        self.setWindowTitle(self.get_text("window_title", "Text-to-Speech Tool"))

        # Language switch button
        self.lang_switch_btn.setText(self.get_text("change_language", "Change Language"))

        # Engine group
        self.engine_group.setTitle(self.get_text("tts_engine", "TTS Engine"))
        self.engine_label.setText(self.get_text("engine", "Engine:"))

        # Language & Voice group
        self.selection_group.setTitle(self.get_text("language_voice", "Language & Voice"))
        self.language_label.setText(self.get_text("language", "Language:"))
        self.voice_label.setText(self.get_text("voice", "Voice:"))

        # Voice settings group
        self.settings_group.setTitle(self.get_text("voice_settings", "Voice Settings"))
        self.rate_label_text.setText(self.get_text("rate", "Rate:"))
        self.volume_label_text.setText(self.get_text("volume", "Volume:"))

        # Text input group
        self.text_group.setTitle(self.get_text("text_to_synthesize", "Text to Synthesize"))
        self.text_edit.setPlaceholderText(self.get_text("text_placeholder", "Enter text here..."))

        # Buttons
        self.synthesize_btn.setText(self.get_text("synthesize", "Synthesize"))
        self.cancel_btn.setText(self.get_text("cancel", "Cancel"))
        self.save_btn.setText(self.get_text("save_audio", "Save Audio"))

        # Status label
        if hasattr(self, 'status_label') and self.status_label.text() in ["Ready", "Sẵn sàng"]:
            self.status_label.setText(self.get_text("ready", "Ready"))

    def load_default_settings(self):
        """Load default settings from config"""
        defaults = self.config.get('default_settings', {})

        # Set default engine
        default_engine = defaults.get('engine', 'edge-tts')
        for i in range(self.engine_combo.count()):
            if self.engine_combo.itemData(i) == default_engine:
                self.engine_combo.setCurrentIndex(i)
                # Trigger language loading for the selected engine
                self.on_engine_changed(i)
                break

    def on_engine_changed(self, index):
        """Handle engine selection change"""
        if index < 0:
            return

        engine_id = self.engine_combo.itemData(index)
        self.current_engine = self.engines.get(engine_id)

        if self.current_engine:
            # Update languages
            self.language_combo.clear()
            languages = self.current_engine.get_available_languages()
            for lang in languages:
                self.language_combo.addItem(lang.get('name', lang['code']), lang)

            # Auto-select first language if available
            if self.language_combo.count() > 0:
                self.on_language_changed(0)

    def on_language_changed(self, index):
        """Handle language selection change"""
        if index < 0 or not self.current_engine:
            return

        language_data = self.language_combo.itemData(index)
        if not language_data:
            return

        # Update voices for selected language
        self.voice_combo.clear()
        voices = self.current_engine.get_available_voices()

        # Filter voices by language
        lang_code = language_data.get('code')  # This will be the language prefix like "en"
        filtered_voices = []

        for voice in voices:
            # Match voices by language prefix
            if voice.get('language_prefix') == lang_code:
                filtered_voices.append(voice)

        # Add filtered voices to combo box
        for voice in filtered_voices:
            display_name = f"{voice['name']} ({voice.get('gender', 'unknown')})"
            self.voice_combo.addItem(display_name, voice['id'])

        # If no voices found, show all voices
        if not self.voice_combo.count():
            for voice in voices:
                display_name = voice.get('name', voice['id'])
                self.voice_combo.addItem(display_name, voice['id'])

    def on_rate_changed(self, value):
        """Handle rate slider change"""
        self.rate_label.setText(f"{value:+d}%")

    def on_volume_changed(self, value):
        """Handle volume slider change"""
        self.volume_label.setText(f"{value:+d}%")

    def on_text_changed(self):
        """Handle text input change"""
        has_text = bool(self.text_edit.toPlainText().strip())
        self.synthesize_btn.setEnabled(has_text and self.current_engine is not None)

    def on_synthesize(self):
        """Handle synthesize button click"""
        if not self.current_engine:
            QMessageBox.warning(self, "Warning", self.get_text("messages.warning_no_engine", "No TTS engine selected!"))
            return

        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Warning", self.get_text("messages.warning_no_text", "Please enter some text!"))
            return

        voice_id = self.voice_combo.currentData()
        if not voice_id:
            QMessageBox.warning(self, "Warning", self.get_text("messages.warning_no_voice", "Please select a voice!"))
            return

        # Disable buttons during synthesis
        self.synthesize_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setVisible(True)

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(self.get_text("synthesizing", "Synthesizing..."))

        # Start synthesis thread
        rate = f"{self.rate_slider.value():+d}%"
        volume = f"{self.volume_slider.value():+d}%"

        self.tts_thread = TTSThread(
            self.current_engine, text, voice_id,
            rate=rate, volume=volume
        )
        self.tts_thread.progress.connect(self.progress_bar.setValue)
        self.tts_thread.finished.connect(self.on_synthesis_finished)
        self.tts_thread.error.connect(self.on_synthesis_error)
        self.tts_thread.cancelled.connect(self.on_synthesis_cancelled)
        self.tts_thread.start()

    def on_synthesis_finished(self, audio_data: bytes, srt_content: str):
        """Handle successful synthesis"""
        self.audio_data = audio_data
        self.srt_content = srt_content
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.status_label.setText(self.get_text("synthesis_completed", "Synthesis completed!"))

        # Auto-save the audio and SRT
        self.auto_save_audio(audio_data, srt_content)

        # Re-enable buttons
        self.synthesize_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        QMessageBox.information(self, "Success", self.get_text("messages.success_synthesized", "Text synthesized and saved successfully!"))

    def on_synthesis_error(self, error_msg: str):
        """Handle synthesis error"""
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.status_label.setText(self.get_text("synthesis_failed", "Synthesis failed!"))

        # Re-enable buttons
        self.synthesize_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        error_text = self.get_text("messages.error_synthesis_failed", "Synthesis failed: {error}").format(error=error_msg)
        QMessageBox.critical(self, "Error", error_text)

    def on_cancel_synthesize(self):
        """Handle cancel synthesis button click"""
        if hasattr(self, 'tts_thread') and self.tts_thread.isRunning():
            self.tts_thread.cancel()
            self.status_label.setText(self.get_text("cancelling_synthesis", "Cancelling synthesis..."))
            self.cancel_btn.setEnabled(False)

    def on_synthesis_cancelled(self):
        """Handle synthesis cancellation"""
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.status_label.setText(self.get_text("synthesis_cancelled", "Synthesis cancelled"))

        # Re-enable buttons
        self.synthesize_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def auto_save_audio(self, audio_data: bytes, srt_content: str):
        """Auto-save audio and SRT files with timestamp folder"""
        from datetime import datetime
        import os

        # Create timestamp folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_path = f"audio_out/{timestamp}"

        try:
            # Create folder if it doesn't exist
            os.makedirs(folder_path, exist_ok=True)

            # Save audio file
            audio_filename = f"{folder_path}/{timestamp}.mp3"
            with open(audio_filename, 'wb') as f:
                f.write(audio_data)

            # Save SRT file
            srt_filename = f"{folder_path}/{timestamp}.srt"
            with open(srt_filename, 'w', encoding='utf-8') as f:
                f.write(srt_content)

            self.status_label.setText(f"Files saved: {audio_filename}, {srt_filename}")

        except Exception as e:
            error_text = self.get_text("messages.warning_save_failed", "Failed to auto-save files: {error}").format(error=str(e))
            QMessageBox.warning(self, "Warning", error_text)

    def on_save_audio(self):
        """Handle save audio button click (now hidden, auto-save is used instead)"""
        pass


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look

    window = TTSApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
