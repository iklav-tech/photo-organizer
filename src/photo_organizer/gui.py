"""Optional PySide6 graphical interface for photo_organizer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from photo_organizer import __app_name__
from photo_organizer.executor import (
    DestinationConflictError,
    apply_operations,
    plan_organization_operations,
)
from photo_organizer.hashing import find_duplicate_image_groups
from photo_organizer.metadata import DATE_HEURISTICS_DEFAULT
from photo_organizer.scanner import find_image_files


class GuiDependencyError(RuntimeError):
    """Raised when the optional GUI dependency is unavailable."""


GUI_INSTALL_MESSAGE = (
    "A interface grafica requer PySide6. Instale a dependencia de GUI com:\n"
    "  python -m pip install 'photo-organizer[gui]'\n"
    "ou, em uma instalacao editavel/local:\n"
    "  python -m pip install PySide6"
)


@dataclass(frozen=True)
class GuiSettings:
    source: str
    output: str
    mode: str
    dry_run: bool
    organization_strategy: str


def _load_qt_modules():
    try:
        from PySide6.QtCore import Qt  # noqa: PLC0415
        from PySide6.QtWidgets import (  # noqa: PLC0415
            QApplication,
            QCheckBox,
            QComboBox,
            QFileDialog,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QPlainTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ModuleNotFoundError as exc:
        missing_name = exc.name or ""
        if missing_name == "PySide6" or missing_name.startswith("PySide6."):
            raise GuiDependencyError(GUI_INSTALL_MESSAGE) from exc
        raise

    return {
        "QApplication": QApplication,
        "QCheckBox": QCheckBox,
        "QComboBox": QComboBox,
        "QFileDialog": QFileDialog,
        "QFormLayout": QFormLayout,
        "QHBoxLayout": QHBoxLayout,
        "QLabel": QLabel,
        "QLineEdit": QLineEdit,
        "QMainWindow": QMainWindow,
        "QMessageBox": QMessageBox,
        "QPlainTextEdit": QPlainTextEdit,
        "QPushButton": QPushButton,
        "QVBoxLayout": QVBoxLayout,
        "QWidget": QWidget,
        "Qt": Qt,
    }


def _format_plan_preview(operations) -> str:
    if not operations:
        return "Nenhuma operacao planejada."

    lines = [f"Operacoes planejadas: {len(operations)}", ""]
    for operation in operations[:100]:
        lines.append(
            f"{operation.mode.upper()}: {operation.source} -> {operation.destination}"
        )
    if len(operations) > 100:
        lines.append(f"... mais {len(operations) - 100} operacoes")
    return "\n".join(lines)


def _format_duplicate_groups(groups) -> str:
    if not groups:
        return "Nenhuma imagem duplicada encontrada."

    lines = [f"Grupos duplicados: {len(groups)}", ""]
    for index, group in enumerate(groups, start=1):
        lines.append(f"Grupo {index}:")
        lines.append(f"  Hash: {group.content_hash}")
        lines.append(f"  Original: {group.original}")
        for duplicate in group.duplicates:
            lines.append(f"  Duplicada: {duplicate}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _build_main_window(qt):
    QApplication = qt["QApplication"]
    QCheckBox = qt["QCheckBox"]
    QComboBox = qt["QComboBox"]
    QFileDialog = qt["QFileDialog"]
    QFormLayout = qt["QFormLayout"]
    QHBoxLayout = qt["QHBoxLayout"]
    QLabel = qt["QLabel"]
    QLineEdit = qt["QLineEdit"]
    QMainWindow = qt["QMainWindow"]
    QMessageBox = qt["QMessageBox"]
    QPlainTextEdit = qt["QPlainTextEdit"]
    QPushButton = qt["QPushButton"]
    QVBoxLayout = qt["QVBoxLayout"]
    QWidget = qt["QWidget"]
    Qt = qt["Qt"]

    class MainWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle(__app_name__)
            self.resize(900, 620)

            self.source_input = QLineEdit()
            self.output_input = QLineEdit()
            self.mode_input = QComboBox()
            self.mode_input.addItems(["copy", "move"])
            self.strategy_input = QComboBox()
            self.strategy_input.addItems(
                ["date", "event", "location", "location-date", "city-state-month"]
            )
            self.dry_run_input = QCheckBox("Dry run")
            self.dry_run_input.setChecked(True)
            self.status_label = QLabel("Pronto")
            self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.output_log = QPlainTextEdit()
            self.output_log.setReadOnly(True)

            source_button = QPushButton("Selecionar")
            source_button.clicked.connect(
                lambda: self._select_directory(self.source_input)
            )
            output_button = QPushButton("Selecionar")
            output_button.clicked.connect(
                lambda: self._select_directory(self.output_input)
            )

            form = QFormLayout()
            form.addRow("Origem", self._path_row(self.source_input, source_button))
            form.addRow("Destino", self._path_row(self.output_input, output_button))
            form.addRow("Modo", self.mode_input)
            form.addRow("Organizar por", self.strategy_input)
            form.addRow("", self.dry_run_input)

            scan_button = QPushButton("Scan")
            scan_button.clicked.connect(self.scan_source)
            dedupe_button = QPushButton("Dedupe")
            dedupe_button.clicked.connect(self.find_duplicates)
            plan_button = QPushButton("Planejar")
            plan_button.clicked.connect(self.preview_plan)
            execute_button = QPushButton("Executar")
            execute_button.clicked.connect(self.execute_plan)

            actions = QHBoxLayout()
            actions.addWidget(scan_button)
            actions.addWidget(dedupe_button)
            actions.addWidget(plan_button)
            actions.addWidget(execute_button)
            actions.addStretch(1)

            root = QVBoxLayout()
            root.addLayout(form)
            root.addLayout(actions)
            root.addWidget(self.status_label)
            root.addWidget(self.output_log, 1)

            container = QWidget()
            container.setLayout(root)
            self.setCentralWidget(container)

        def _path_row(self, input_widget, button):
            row = QHBoxLayout()
            row.addWidget(input_widget, 1)
            row.addWidget(button)
            container = QWidget()
            container.setLayout(row)
            return container

        def _select_directory(self, target) -> None:
            directory = QFileDialog.getExistingDirectory(self, "Selecionar pasta")
            if directory:
                target.setText(directory)

        def _settings(self, require_output: bool) -> GuiSettings | None:
            source = self.source_input.text().strip()
            output = self.output_input.text().strip()
            if not source:
                QMessageBox.warning(
                    self,
                    "Campo obrigatorio",
                    "Informe a pasta de origem.",
                )
                return None
            if require_output and not output:
                QMessageBox.warning(
                    self,
                    "Campo obrigatorio",
                    "Informe a pasta de destino.",
                )
                return None
            return GuiSettings(
                source=source,
                output=output,
                mode=self.mode_input.currentText(),
                dry_run=self.dry_run_input.isChecked(),
                organization_strategy=self.strategy_input.currentText(),
            )

        def _run_action(self, label: str, action: Callable[[], str]) -> None:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.status_label.setText(f"{label}...")
            try:
                self.output_log.setPlainText(action())
                self.status_label.setText("Concluido")
            except (
                FileNotFoundError,
                NotADirectoryError,
                DestinationConflictError,
                ValueError,
            ) as exc:
                self.status_label.setText("Erro")
                QMessageBox.critical(self, "Erro", str(exc))
            finally:
                QApplication.restoreOverrideCursor()

        def scan_source(self) -> None:
            settings = self._settings(require_output=False)
            if settings is None:
                return

            def action() -> str:
                files = find_image_files(settings.source, recursive=True)
                lines = [f"Arquivos suportados: {len(files)}", ""]
                lines.extend(str(path) for path in files[:500])
                if len(files) > 500:
                    lines.append(f"... mais {len(files) - 500} arquivos")
                return "\n".join(lines)

            self._run_action("Escaneando", action)

        def find_duplicates(self) -> None:
            settings = self._settings(require_output=False)
            if settings is None:
                return
            self._run_action(
                "Procurando duplicadas",
                lambda: _format_duplicate_groups(
                    find_duplicate_image_groups(settings.source, recursive=True)
                ),
            )

        def _plan_operations(self, settings: GuiSettings):
            return plan_organization_operations(
                settings.source,
                settings.output,
                mode=settings.mode,
                organization_strategy=settings.organization_strategy,
                reverse_geocode=settings.organization_strategy
                in {"location", "location-date", "city-state-month"},
                reconciliation_policy="precedence",
                date_heuristics=DATE_HEURISTICS_DEFAULT,
                location_inference=True,
            )

        def preview_plan(self) -> None:
            settings = self._settings(require_output=True)
            if settings is None:
                return

            def action() -> str:
                plan_result = self._plan_operations(settings)
                operations = (
                    plan_result[0] if isinstance(plan_result, tuple) else plan_result
                )
                return _format_plan_preview(operations)

            self._run_action("Planejando", action)

        def execute_plan(self) -> None:
            settings = self._settings(require_output=True)
            if settings is None:
                return

            def action() -> str:
                plan_result = self._plan_operations(settings)
                operations = (
                    plan_result[0] if isinstance(plan_result, tuple) else plan_result
                )
                logs = apply_operations(
                    operations,
                    dry_run=settings.dry_run,
                    conflict_quarantine_dir=Path(settings.output) / ".quarantine",
                )
                summary = [
                    f"Operacoes: {len(logs)}",
                    f"Modo: {'dry-run' if settings.dry_run else 'execute'}",
                    "",
                ]
                summary.extend(logs)
                return "\n".join(summary)

            self._run_action("Executando", action)

    return MainWindow


def run(argv: list[str] | None = None) -> int:
    """Run the optional Qt application."""
    del argv
    qt = _load_qt_modules()
    QApplication = qt["QApplication"]
    app = QApplication.instance() or QApplication([])
    window_type = _build_main_window(qt)
    window = window_type()
    window.show()
    return app.exec()
