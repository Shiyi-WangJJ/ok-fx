from PySide6.QtCore import Qt
from qfluentwidgets import BodyLabel

from ok.gui.about.VersionCard import VersionCard
from ok.gui.util.pyappify_startup import get_startup_version_change
from ok.gui.widget.Tab import Tab
from ok.util.file import get_path_relative_to_exe


class AboutTab(Tab):
    def __init__(self, config):
        super().__init__()
        self.version_card = VersionCard(config, get_path_relative_to_exe(config.get('gui_icon')),
                                        config.get('gui_title'), config.get('version'),
                                        config.get('debug'), self)
        self.vBoxLayout.setSpacing(0)
        # Create a QTextEdit instance
        self.add_widget(self.version_card)
        self.vBoxLayout.addSpacing(12)

        if version_change := get_startup_version_change():
            update_note_label = BodyLabel()
            update_note_label.setText(version_change.content)
            update_note_label.setWordWrap(True)
            update_note_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            update_note_label.setContentsMargins(0, 0, 0, 0)
            self.add_card(self._startup_version_change_title(version_change), update_note_label)
            self.vBoxLayout.addSpacing(12)

        if about := config.get('about'):
            about_label = BodyLabel()
            about_label.setText(about)
            about_label.setWordWrap(True)
            about_label.setOpenExternalLinks(True)
            about_label.setContentsMargins(0, 0, 0, 0)

            self.add_widget(about_label)

        self.vBoxLayout.addStretch(1)

        disclaimer = BodyLabel()
        disclaimer.setText(
            "本软件是免费开源的。如果你被收费，请立即退款。\n"
            "请访问QQ频道或GitHub下载最新的官方版本。\n\n"
            "本软件仅供个人使用，用于学习Python编程、计算机视觉、\n"
            "UI自动化等。请勿将其用于任何营利性或商业用途。"
        )
        disclaimer.setStyleSheet("color: #ff4444; font-size: 12px;")
        disclaimer.setWordWrap(True)
        disclaimer.setContentsMargins(0, 12, 0, 12)
        self.add_widget(disclaimer)

    def _startup_version_change_title(self, version_change):
        if version_change.action == "update":
            title = self.tr("Update success {from_version} -> {to_version}")
        elif version_change.action == "downgrade":
            title = self.tr("Downgrade success {from_version} -> {to_version}")
        else:
            return version_change.title
        return title.format(from_version=version_change.from_version, to_version=version_change.to_version)
