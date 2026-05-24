"""Main organize workflow page."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from photo_organizer.executor import DestinationConflictError, FileOperation
from photo_organizer.hashing import DuplicateGroup
from photo_organizer.gui.adapters.organizer import GuiSettings, OrganizerAdapter
from photo_organizer.gui.widgets import PathPicker


class OrganizePage(QWidget):
    """Page that exposes scan, dedupe, plan and execute actions."""

    def __init__(
        self,
        adapter: OrganizerAdapter,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._build_ui()

    def _build_ui(self) -> None:
        self.source_picker = PathPicker(caption="Selecionar pasta de origem")
        self.output_picker = PathPicker(caption="Selecionar pasta de destino")
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

        form = QFormLayout()
        form.addRow("Origem", self.source_picker)
        form.addRow("Destino", self.output_picker)
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

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)
        layout.addWidget(self.output_log, 1)
        self.setLayout(layout)

    def _settings(self, *, require_output: bool) -> GuiSettings | None:
        source = self.source_picker.text()
        output = self.output_picker.text()
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
            files = self._adapter.scan(settings.source)
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
            lambda: self._format_duplicate_groups(
                self._adapter.find_duplicates(settings.source)
            ),
        )

    def preview_plan(self) -> None:
        settings = self._settings(require_output=True)
        if settings is None:
            return
        self._run_action(
            "Planejando",
            lambda: self._format_plan_preview(self._adapter.plan(settings)),
        )

    def execute_plan(self) -> None:
        settings = self._settings(require_output=True)
        if settings is None:
            return

        def action() -> str:
            logs = self._adapter.execute(settings)
            summary = [
                f"Operacoes: {len(logs)}",
                f"Modo: {'dry-run' if settings.dry_run else 'execute'}",
                f"Quarentena: {Path(settings.output) / '.quarantine'}",
                "",
            ]
            summary.extend(logs)
            return "\n".join(summary)

        self._run_action("Executando", action)

    def _format_plan_preview(self, operations: list[FileOperation]) -> str:
        if not operations:
            return "Nenhuma operacao planejada."

        lines = [f"Operacoes planejadas: {len(operations)}", ""]
        for operation in operations[:100]:
            lines.append(
                f"{operation.mode.upper()}: "
                f"{operation.source} -> {operation.destination}"
            )
        if len(operations) > 100:
            lines.append(f"... mais {len(operations) - 100} operacoes")
        return "\n".join(lines)

    def _format_duplicate_groups(self, groups: list[DuplicateGroup]) -> str:
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
