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
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from photo_organizer.executor import DestinationConflictError, FileOperation
from photo_organizer.hashing import DuplicateGroup
from photo_organizer.gui.adapters.organizer import GuiSettings, OrganizerAdapter
from photo_organizer.gui.session import SessionMetrics, SessionState
from photo_organizer.gui.theme import SPACING, set_theme_role
from photo_organizer.gui.widgets import PathPicker


class OrganizePage(QWidget):
    """Page that exposes scan, dedupe, plan and execute actions."""

    def __init__(
        self,
        adapter: OrganizerAdapter,
        session: SessionState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self.session = session
        self._build_ui()
        self.session.source_directory_changed.connect(self._set_source_directory)
        self.session.metrics_changed.connect(self._update_metrics)

    def _build_ui(self) -> None:
        set_theme_role(self, "page")
        self.source_picker = PathPicker(caption="Selecionar pasta de origem")
        self.source_picker.directory_selected.connect(self._source_directory_selected)
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
        set_theme_role(self.status_label, "badgePrimary")
        self.output_log = QPlainTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setPlaceholderText("System engine output will appear here...")
        set_theme_role(self.output_log, "logPanel")

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(SPACING.md)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
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
        set_theme_role(execute_button, "primaryButton")
        execute_button.clicked.connect(self.execute_plan)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(SPACING.sm)
        actions.addWidget(scan_button)
        actions.addWidget(dedupe_button)
        actions.addWidget(plan_button)
        actions.addWidget(execute_button)
        actions.addStretch(1)

        self.source_path_label = QLabel("SOURCE PATH: not selected")
        set_theme_role(self.source_path_label, "metadata")
        title = QLabel("Session Overview")
        set_theme_role(title, "headline")
        self.scan_badge = QLabel("SCAN_COMPLETE: --")
        set_theme_role(self.scan_badge, "badge")
        live_badge = QLabel("LIVE_TRACKING")
        set_theme_role(live_badge, "badgePrimary")

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header_title = QVBoxLayout()
        header_title.setSpacing(SPACING.xs)
        header_title.addWidget(self.source_path_label)
        header_title.addWidget(title)
        header.addLayout(header_title)
        header.addStretch(1)
        header.addWidget(self.scan_badge)
        header.addWidget(live_badge)

        form_card = self._card("ORGANIZE SETTINGS", form)
        stats_card = self._build_stats_card()
        integrity_card = self._build_integrity_card()
        hero_card = self._build_hero_card()
        log_card = self._build_log_card()

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(SPACING.md)
        grid.setVerticalSpacing(SPACING.md)
        grid.addWidget(form_card, 0, 0, 1, 2)
        grid.addWidget(stats_card, 1, 0)
        grid.addWidget(integrity_card, 1, 1)
        grid.addWidget(hero_card, 2, 0, 1, 2)

        layout = QVBoxLayout()
        layout.setContentsMargins(SPACING.lg, SPACING.lg, SPACING.lg, SPACING.lg)
        layout.setSpacing(SPACING.md)
        layout.addLayout(header)
        layout.addLayout(grid)
        layout.addLayout(actions)
        layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(log_card, 1)
        self.setLayout(layout)

    def _card(self, title: str, body: QFormLayout | QVBoxLayout) -> QWidget:
        card = QWidget()
        set_theme_role(card, "card")
        label = QLabel(title)
        set_theme_role(label, "sectionLabel")

        layout = QVBoxLayout()
        layout.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        layout.setSpacing(SPACING.md)
        layout.addWidget(label)
        layout.addLayout(body)
        card.setLayout(layout)
        return card

    def _build_stats_card(self) -> QWidget:
        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(SPACING.sm)
        self.total_files_metric = QLabel("--")
        set_theme_role(self.total_files_metric, "metric")
        caption = QLabel("Arquivos escaneados")
        set_theme_role(caption, "muted")
        body.addWidget(self.total_files_metric)
        body.addWidget(caption)
        body.addWidget(self._mini_stat_row("JPG", "--"))
        body.addWidget(self._mini_stat_row("RAW", "--"))
        return self._card("TOTAL FILES INGESTED", body)

    def _mini_stat_row(self, label: str, value: str) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        name = QLabel(label)
        set_theme_role(name, "code")
        amount = QLabel(value)
        set_theme_role(amount, "code")
        row_layout.addWidget(name)
        row_layout.addStretch(1)
        row_layout.addWidget(amount)
        row.setLayout(row_layout)
        return row

    def _build_integrity_card(self) -> QWidget:
        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(SPACING.sm)
        body.addLayout(self._progress_row("GPS Coordinates", 88))
        body.addLayout(self._progress_row("Timestamp Sync", 100))
        body.addLayout(self._progress_row("Camera Profiles", 92, secondary=True))
        return self._card("EXIF INTEGRITY", body)

    def _progress_row(
        self,
        label: str,
        value: int,
        *,
        secondary: bool = False,
    ) -> QVBoxLayout:
        row = QVBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SPACING.xs)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        name = QLabel(label)
        set_theme_role(name, "code")
        percent = QLabel(f"{value}%")
        set_theme_role(percent, "code")
        header.addWidget(name)
        header.addStretch(1)
        header.addWidget(percent)
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(value)
        progress.setTextVisible(False)
        if secondary:
            set_theme_role(progress, "secondaryProgress")
        row.addLayout(header)
        row.addWidget(progress)
        return row

    def _build_hero_card(self) -> QWidget:
        card = QWidget()
        set_theme_role(card, "heroCard")
        title = QLabel("Intelligent Sort")
        set_theme_role(title, "heroTitle")
        text = QLabel(
            "Distribua fotos em hierarquias por data, local e metadados "
            "mantendo rastreabilidade operacional."
        )
        text.setWordWrap(True)
        set_theme_role(text, "heroText")
        time = QLabel("EST. TIME: depende do volume")
        set_theme_role(time, "metadata")
        layout = QVBoxLayout()
        layout.setContentsMargins(SPACING.md, SPACING.md, SPACING.md, SPACING.md)
        layout.setSpacing(SPACING.sm)
        layout.addWidget(title)
        layout.addWidget(text)
        layout.addStretch(1)
        layout.addWidget(time)
        card.setLayout(layout)
        return card

    def _build_log_card(self) -> QWidget:
        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(SPACING.sm)
        body.addWidget(self.output_log)
        return self._card("SYSTEM ENGINE OUTPUT", body)

    def _settings(self, *, require_output: bool) -> GuiSettings | None:
        source = self.session.source_directory or self.source_picker.text()
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
            metrics = self._adapter.scan_metrics(files)
            metadata_health = (
                self._adapter.metadata_health(files)
                if hasattr(self._adapter, "metadata_health")
                else None
            )
            self.session.set_scan_result(
                files,
                total_size_bytes=metrics.total_size_bytes,
                by_extension=metrics.by_extension,
                by_format=metrics.by_format,
                metadata_health=metadata_health,
            )
            self.session.add_log(f"Scan completed for {settings.source}: {len(files)} files")
            self.total_files_metric.setText(f"{len(files):,}")
            self.scan_badge.setText("SCAN_COMPLETE: 100%")
            self.source_path_label.setText(f"SOURCE PATH: {settings.source}")
            lines = [f"Arquivos suportados: {len(files)}", ""]
            lines.extend(str(path) for path in files[:500])
            if len(files) > 500:
                lines.append(f"... mais {len(files) - 500} arquivos")
            return "\n".join(lines)

        self._run_action("Escaneando", action)

    def _source_directory_selected(self, source_directory: str) -> None:
        self.session.set_source_directory(source_directory)
        self.scan_source()

    def _set_source_directory(self, source_directory: str) -> None:
        if self.source_picker.text() != source_directory:
            self.source_picker.set_text(source_directory)
        self.source_path_label.setText(f"SOURCE PATH: {source_directory}")

    def _update_metrics(self, metrics: SessionMetrics) -> None:
        self.total_files_metric.setText(f"{metrics.total_files:,}")
        self.scan_badge.setText(
            "SCAN_COMPLETE: 100%" if metrics.total_files else "SCAN_COMPLETE: --"
        )

    def find_duplicates(self) -> None:
        settings = self._settings(require_output=False)
        if settings is None:
            return

        def action() -> str:
            groups = self._adapter.find_duplicates(settings.source)
            self.session.set_duplicate_groups(groups)
            self.session.add_log(
                f"Duplicate scan completed for {settings.source}: {len(groups)} groups"
            )
            return self._format_duplicate_groups(groups)

        self._run_action("Procurando duplicadas", action)

    def preview_plan(self) -> None:
        settings = self._settings(require_output=True)
        if settings is None:
            return

        def action() -> str:
            operations = self._adapter.plan(settings)
            self.session.set_preview_operations(operations)
            self.session.add_log(
                f"Plan preview completed for {settings.source}: {len(operations)} operations"
            )
            return self._format_plan_preview(operations)

        self._run_action("Planejando", action)

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
