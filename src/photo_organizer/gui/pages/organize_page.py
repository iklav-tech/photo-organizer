"""Main organize workflow page."""

from __future__ import annotations

import logging
import multiprocessing
import tempfile
from collections.abc import Callable
from concurrent.futures import BrokenExecutor, Future, ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Queue

from PySide6.QtCore import QThread, QTimer, Qt, Slot
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from photo_organizer.executor import DestinationConflictError, FileOperation
from photo_organizer.hashing import DuplicateGroup
from photo_organizer.gui.adapters.organizer import GuiSettings, OrganizerAdapter
from photo_organizer.gui.logging_bridge import (
    FileLogEventReader,
    FileLogEventWriter,
    drain_gui_log_queue,
    install_gui_log_handler,
)
from photo_organizer.gui.session import (
    LogEvent,
    MetadataHealth,
    SessionMetrics,
    SessionState,
    TaskProgress,
)
from photo_organizer.gui.theme import SPACING, set_theme_role
from photo_organizer.gui.widgets import LogConsole, PathPicker
from photo_organizer.gui.workers import TaskWorker
from photo_organizer.gui.workers.task_worker import TaskReporter


@dataclass(frozen=True)
class ScanResult:
    source: str
    files: list[Path]
    total_size_bytes: int
    by_extension: dict[str, int]
    by_format: dict[str, int]
    metadata_health: MetadataHealth | None
    output: str


@dataclass(frozen=True)
class DuplicateResult:
    groups: list[DuplicateGroup]
    output: str


@dataclass(frozen=True)
class PlanResult:
    operations: list[FileOperation]
    output: str


@dataclass(frozen=True)
class ExecuteResult:
    logs: list[str]
    output: str


def _scan_with_default_adapter(
    settings: GuiSettings,
    event_sink: str | Queue[LogEvent] | FileLogEventWriter | None = None,
) -> ScanResult:
    _prepare_backend_process(event_sink)
    adapter = OrganizerAdapter()
    files = adapter.scan(settings.source)
    metrics = adapter.scan_metrics(files)
    metadata_health = adapter.metadata_health(files)
    return _make_scan_result(settings.source, files, metrics, metadata_health)


def _plan_with_default_adapter(
    settings: GuiSettings,
    event_sink: str | Queue[LogEvent] | FileLogEventWriter | None = None,
) -> PlanResult:
    _prepare_backend_process(event_sink)
    operations = OrganizerAdapter().plan(settings)
    return PlanResult(
        operations=operations,
        output=_format_plan_preview(operations),
    )


def _execute_with_default_adapter(
    settings: GuiSettings,
    event_sink: str | Queue[LogEvent] | FileLogEventWriter | None = None,
) -> ExecuteResult:
    _prepare_backend_process(event_sink)
    logs = OrganizerAdapter().execute(settings)
    return _make_execute_result(settings, logs)


def _run_in_process(task: Callable[[GuiSettings], object], settings: GuiSettings) -> object:
    try:
        with ProcessPoolExecutor(
            max_workers=1,
            mp_context=_backend_process_context(),
        ) as executor:
            return executor.submit(task, settings).result()
    except BrokenExecutor as exc:
        raise _backend_process_crash_error(exc) from exc


def _backend_process_crash_error(_exc: Exception) -> RuntimeError:
    return RuntimeError(
        "Backend worker process crashed while processing media metadata. "
        "The GUI was kept alive; check the last logged file and native HEIF/EXIF "
        "dependencies."
    )


def _backend_process_context():
    return multiprocessing.get_context("spawn")


def _prepare_backend_process(
    event_sink: str | Queue[LogEvent] | FileLogEventWriter | None = None,
) -> None:
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if handler.__class__.__name__ == "GuiLogHandler":
            root_logger.removeHandler(handler)
    if event_sink is None:
        return
    if isinstance(event_sink, str):
        install_gui_log_handler(FileLogEventWriter(event_sink))
    else:
        install_gui_log_handler(event_sink)


def _make_scan_result(
    source: str,
    files: list[Path],
    metrics: object,
    metadata_health: MetadataHealth | None,
) -> ScanResult:
    lines = [f"Arquivos suportados: {len(files)}", ""]
    lines.extend(str(path) for path in files[:500])
    if len(files) > 500:
        lines.append(f"... mais {len(files) - 500} arquivos")
    return ScanResult(
        source=source,
        files=files,
        total_size_bytes=metrics.total_size_bytes,
        by_extension=metrics.by_extension,
        by_format=metrics.by_format,
        metadata_health=metadata_health,
        output="\n".join(lines),
    )


def _make_execute_result(settings: GuiSettings, logs: list[str]) -> ExecuteResult:
    summary = [
        f"Operacoes: {len(logs)}",
        f"Modo: {'dry-run' if settings.dry_run else 'execute'}",
        f"Quarentena: {Path(settings.output) / '.quarantine'}",
        "",
    ]
    summary.extend(logs)
    return ExecuteResult(logs=logs, output="\n".join(summary))


def _format_plan_preview(operations: list[FileOperation]) -> str:
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


def _format_duplicate_groups(
    groups: list[DuplicateGroup],
    *,
    max_groups: int = 100,
    max_duplicates_per_group: int = 20,
) -> str:
    if not groups:
        return "Nenhuma imagem duplicada encontrada."

    duplicate_files = sum(len(group.duplicates) for group in groups)
    lines = [
        f"Grupos duplicados: {len(groups)}",
        f"Arquivos duplicados: {duplicate_files}",
        "",
    ]
    for index, group in enumerate(groups[:max_groups], start=1):
        lines.append(f"Grupo {index}:")
        lines.append(f"  Hash: {group.content_hash}")
        lines.append(f"  Original: {group.original}")
        for duplicate in group.duplicates[:max_duplicates_per_group]:
            lines.append(f"  Duplicada: {duplicate}")
        hidden_duplicates = len(group.duplicates) - max_duplicates_per_group
        if hidden_duplicates > 0:
            lines.append(f"  ... mais {hidden_duplicates} duplicadas neste grupo")
        lines.append("")
    hidden_groups = len(groups) - max_groups
    if hidden_groups > 0:
        lines.append(f"... mais {hidden_groups} grupos duplicados")
    return "\n".join(lines).rstrip()


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
        self._task_thread: QThread | None = None
        self._task_worker: TaskWorker[object] | None = None
        self._task_label = ""
        self._task_on_finished: Callable[[object], None] | None = None
        self._process_executor: ProcessPoolExecutor | None = None
        self._process_future: Future[object] | None = None
        self._process_timer: QTimer | None = None
        self._process_log_queue: FileLogEventReader | None = None
        self._process_log_path: Path | None = None
        self._process_label = ""
        self._process_on_finished: Callable[[object], None] | None = None
        self._build_ui()
        self.session.source_directory_changed.connect(self._set_source_directory)
        self.session.metrics_changed.connect(self._update_metrics)
        self.session.log_event_added.connect(self._append_log_event)
        self.session.task_progress_changed.connect(self._update_task_progress)

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
        self.output_log = LogConsole()

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(SPACING.md)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.addRow("Origem", self.source_picker)
        form.addRow("Destino", self.output_picker)
        form.addRow("Modo", self.mode_input)
        form.addRow("Organizar por", self.strategy_input)
        form.addRow("", self.dry_run_input)

        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self.scan_source)
        self.dedupe_button = QPushButton("Dedupe")
        self.dedupe_button.clicked.connect(self.find_duplicates)
        self.plan_button = QPushButton("Planejar")
        self.plan_button.clicked.connect(self.preview_plan)
        self.execute_button = QPushButton("Executar")
        set_theme_role(self.execute_button, "primaryButton")
        self.execute_button.clicked.connect(self.execute_plan)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(SPACING.sm)
        actions.addWidget(self.scan_button)
        actions.addWidget(self.dedupe_button)
        actions.addWidget(self.plan_button)
        actions.addWidget(self.execute_button)
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

    def _run_action(
        self,
        label: str,
        action: Callable[[TaskReporter], object],
        on_finished: Callable[[object], None],
    ) -> None:
        if self._has_running_task():
            self.session.add_log(
                "A task is already running; wait for it to finish.",
                level="WARNING",
                source="gui",
            )
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.status_label.setText(f"{label}...")
        self._set_actions_enabled(False)
        self.session.add_log(f"{label} started.", source="task")

        thread = QThread(self)
        worker: TaskWorker[object] = TaskWorker(action)
        worker.moveToThread(thread)
        self._task_thread = thread
        self._task_worker = worker
        self._task_label = label
        self._task_on_finished = on_finished

        thread.started.connect(worker.run)
        worker.progress.connect(self.session.report_progress)
        worker.log_event.connect(self.session.add_log_event)
        worker.finished.connect(self._finish_current_action)
        worker.failed.connect(self._fail_action)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_task_thread)
        thread.start()

    def _run_process_action(
        self,
        label: str,
        task: Callable[..., object],
        settings: GuiSettings,
        on_finished: Callable[[object], None],
    ) -> None:
        if self._has_running_task():
            self.session.add_log(
                "A task is already running; wait for it to finish.",
                level="WARNING",
                source="gui",
            )
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.status_label.setText(f"{label}...")
        self._set_actions_enabled(False)
        self.session.add_log(f"{label} started.", source="task")
        self.session.report_progress(
            TaskProgress(label=label, current=0, total=1, detail=settings.source)
        )

        context = _backend_process_context()
        spool = tempfile.NamedTemporaryFile(
            prefix="photo-organizer-gui-logs-",
            suffix=".jsonl",
            delete=False,
        )
        spool.close()
        log_path = Path(spool.name)
        log_reader = FileLogEventReader(log_path)
        executor = ProcessPoolExecutor(
            max_workers=1,
            mp_context=context,
        )
        timer = QTimer(self)
        timer.setInterval(50)
        timer.timeout.connect(self._poll_process_action)

        self._process_executor = executor
        self._process_future = executor.submit(task, settings, str(log_path))
        self._process_timer = timer
        self._process_log_queue = log_reader
        self._process_log_path = log_path
        self._process_label = label
        self._process_on_finished = on_finished
        timer.start()

    @Slot()
    def _poll_process_action(self) -> None:
        self._drain_process_logs()
        future = self._process_future
        if future is None or not future.done():
            return

        label = self._process_label
        on_finished = self._process_on_finished
        try:
            result = future.result()
            self.session.report_progress(
                TaskProgress(label=label, current=1, total=1, detail="complete")
            )
            if on_finished is None:
                raise RuntimeError("Task finished without a handler.")
            self._finish_action(label, result, on_finished)
        except BrokenExecutor as exc:
            self._fail_action(_backend_process_crash_error(exc))
        except Exception as exc:
            self._fail_action(exc)
        finally:
            self._drain_process_logs()
            self._clear_process_action()

    @Slot(object)
    def _finish_current_action(self, result: object) -> None:
        if self._task_on_finished is None:
            self._show_action_error(RuntimeError("Task finished without a handler."))
            return
        self._finish_action(self._task_label, result, self._task_on_finished)

    def _finish_action(
        self,
        label: str,
        result: object,
        on_finished: Callable[[object], None],
    ) -> None:
        try:
            on_finished(result)
            self.status_label.setText("Concluido")
            self.session.add_log(f"{label} completed.", source="task")
        except Exception as exc:
            self._show_action_error(exc)

    @Slot(Exception)
    def _fail_action(self, exc: Exception) -> None:
        self._show_action_error(exc)

    def _show_action_error(self, exc: Exception) -> None:
        self.status_label.setText("Erro")
        self.session.add_log(str(exc), level="ERROR", source="task")
        if isinstance(
            exc,
            (
                FileNotFoundError,
                NotADirectoryError,
                DestinationConflictError,
                ValueError,
            ),
        ):
            QMessageBox.critical(self, "Erro", str(exc))
        else:
            QMessageBox.critical(self, "Erro", f"Unexpected error: {exc}")

    def _clear_task_thread(self) -> None:
        self._task_thread = None
        self._task_worker = None
        self._task_label = ""
        self._task_on_finished = None
        self._set_actions_enabled(True)
        QApplication.restoreOverrideCursor()

    def _clear_process_action(self) -> None:
        if self._process_timer is not None:
            self._process_timer.stop()
            self._process_timer.deleteLater()
        if self._process_executor is not None:
            self._process_executor.shutdown(wait=False, cancel_futures=True)
        if self._process_log_path is not None:
            self._process_log_path.unlink(missing_ok=True)
        self._process_executor = None
        self._process_future = None
        self._process_timer = None
        self._process_log_queue = None
        self._process_log_path = None
        self._process_label = ""
        self._process_on_finished = None
        self._set_actions_enabled(True)
        QApplication.restoreOverrideCursor()

    def _drain_process_logs(self) -> None:
        if self._process_log_queue is None:
            return
        drain_gui_log_queue(self._process_log_queue, self.session)

    def _has_running_task(self) -> bool:
        return self._task_thread is not None or self._process_future is not None

    def _uses_default_adapter(self) -> bool:
        return type(self._adapter) is OrganizerAdapter

    def _set_actions_enabled(self, enabled: bool) -> None:
        for button in (
            self.scan_button,
            self.dedupe_button,
            self.plan_button,
            self.execute_button,
        ):
            button.setEnabled(enabled)

    def _append_log_event(self, event: object) -> None:
        self.output_log.append_event(event)

    def _update_task_progress(self, progress: TaskProgress) -> None:
        percent = progress.percent
        if percent is None:
            self.status_label.setText(progress.label)
            return
        self.status_label.setText(f"{progress.label}: {percent}%")

    def scan_source(self) -> None:
        settings = self._settings(require_output=False)
        if settings is None:
            return

        if self._uses_default_adapter():
            self._run_process_action(
                "Escaneando",
                _scan_with_default_adapter,
                settings,
                self._apply_scan_result,
            )
            return

        def action(reporter: TaskReporter) -> ScanResult:
            reporter.progress("Scanning", current=0, total=3, detail=settings.source)
            files = self._adapter.scan(settings.source)
            reporter.progress("Scanning", current=1, total=3, detail=f"{len(files)} files")
            metrics = self._adapter.scan_metrics(files)
            reporter.progress("Scanning", current=2, total=3, detail="metadata health")
            metadata_health = (
                self._adapter.metadata_health(files)
                if hasattr(self._adapter, "metadata_health")
                else None
            )
            reporter.progress("Scanning", current=3, total=3, detail="complete")
            return _make_scan_result(settings.source, files, metrics, metadata_health)

        self._run_action("Escaneando", action, self._apply_scan_result)

    def _apply_scan_result(self, result: object) -> None:
        scan = result
        if not isinstance(scan, ScanResult):
            raise TypeError("Unexpected scan result")
        self.session.set_scan_result(
            scan.files,
            total_size_bytes=scan.total_size_bytes,
            by_extension=scan.by_extension,
            by_format=scan.by_format,
            metadata_health=scan.metadata_health,
        )
        self.session.add_log(
            f"Scan completed for {scan.source}: {len(scan.files)} files",
            source="backend",
        )
        self.total_files_metric.setText(f"{len(scan.files):,}")
        self.scan_badge.setText("SCAN_COMPLETE: 100%")
        self.source_path_label.setText(f"SOURCE PATH: {scan.source}")
        self.output_log.set_plain_output(scan.output, source="scan")

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

        def action(reporter: TaskReporter) -> DuplicateResult:
            reporter.progress("Dedupe", current=0, total=1, detail=settings.source)
            groups = self._adapter.find_duplicates(settings.source)
            reporter.progress("Dedupe", current=1, total=1, detail=f"{len(groups)} groups")
            return DuplicateResult(groups=groups, output=_format_duplicate_groups(groups))

        self._run_action("Procurando duplicadas", action, self._apply_duplicate_result)

    def _apply_duplicate_result(self, result: object) -> None:
        dedupe = result
        if not isinstance(dedupe, DuplicateResult):
            raise TypeError("Unexpected duplicate result")
        self.session.set_duplicate_groups(dedupe.groups)
        self.session.add_log(
            f"Duplicate scan completed: {len(dedupe.groups)} groups",
            source="backend",
        )
        self.output_log.set_plain_output(dedupe.output, source="dedupe")

    def preview_plan(self) -> None:
        settings = self._settings(require_output=True)
        if settings is None:
            return

        if self._uses_default_adapter():
            self._run_process_action(
                "Planejando",
                _plan_with_default_adapter,
                settings,
                self._apply_plan_result,
            )
            return

        def action(reporter: TaskReporter) -> PlanResult:
            reporter.progress("Planning", current=0, total=1, detail=settings.source)
            operations = self._adapter.plan(settings)
            reporter.progress(
                "Planning",
                current=1,
                total=1,
                detail=f"{len(operations)} operations",
            )
            return PlanResult(
                operations=operations,
                output=_format_plan_preview(operations),
            )

        self._run_action("Planejando", action, self._apply_plan_result)

    def _apply_plan_result(self, result: object) -> None:
        plan = result
        if not isinstance(plan, PlanResult):
            raise TypeError("Unexpected plan result")
        self.session.set_preview_operations(plan.operations)
        self.session.add_log(
            f"Plan preview completed: {len(plan.operations)} operations",
            source="backend",
        )
        self.output_log.set_plain_output(plan.output, source="plan")

    def execute_plan(self) -> None:
        settings = self._settings(require_output=True)
        if settings is None:
            return

        if self._uses_default_adapter():
            self._run_process_action(
                "Executando",
                _execute_with_default_adapter,
                settings,
                self._apply_execute_result,
            )
            return

        def action(reporter: TaskReporter) -> ExecuteResult:
            reporter.progress("Executing", current=0, total=1, detail=settings.source)
            logs = self._adapter.execute(settings)
            reporter.progress("Executing", current=1, total=1, detail=f"{len(logs)} logs")
            return _make_execute_result(settings, logs)

        self._run_action("Executando", action, self._apply_execute_result)

    def _apply_execute_result(self, result: object) -> None:
        execute = result
        if not isinstance(execute, ExecuteResult):
            raise TypeError("Unexpected execute result")
        for line in execute.logs:
            if line.startswith("[ERROR]"):
                level = "ERROR"
            elif line.startswith("[SKIP]") or "warning" in line.lower():
                level = "WARNING"
            else:
                level = "INFO"
            self.session.add_log(line, level=level, source="backend")
        self.output_log.set_plain_output(execute.output, source="execute")
