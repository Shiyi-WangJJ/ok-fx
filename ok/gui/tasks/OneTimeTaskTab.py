from ok import Logger, og

from ok.gui.tasks.TaskCard import TaskCard
from ok.gui.tasks.TaskTab import TaskTab

logger = Logger.get_logger(__name__)


class OneTimeTaskTab(TaskTab):
    def __init__(self, is_standalone=True, group_name=None):
        super().__init__()
        self.is_standalone = is_standalone
        self.group_name = group_name
        self.card_widgets = []
        self.keep_info_when_done = True

        # ---- 全自动启动按钮 ----
        from PySide6.QtWidgets import QHBoxLayout
        from qfluentwidgets import PushButton, FluentIcon

        self.auto_btn_layout = QHBoxLayout()
        self.auto_btn_layout.setContentsMargins(0, 6, 0, 6)

        self.auto_start_btn = PushButton(FluentIcon.PLAY, self.tr("▶ 全自动启动"))
        self.auto_start_btn.setStyleSheet("""
            PushButton {
                font-size: 15px; font-weight: bold;
                padding: 10px 28px;
                background-color: #0078D4; color: white;
                border-radius: 6px;
            }
            PushButton:hover {
                background-color: #106EBE;
            }
            PushButton:pressed {
                background-color: #005A9E;
            }
        """)
        self.auto_start_btn.clicked.connect(self._on_auto_start_all)
        self.auto_btn_layout.addWidget(self.auto_start_btn)

        self.stop_all_btn = PushButton(FluentIcon.CANCEL_MEDIUM, self.tr("全部停止"))
        self.stop_all_btn.setStyleSheet("""
            PushButton {
                font-size: 15px; font-weight: bold;
                padding: 10px 28px;
                background-color: #D83B01; color: white;
                border-radius: 6px;
            }
            PushButton:hover {
                background-color: #C33400;
            }
            PushButton:pressed {
                background-color: #A52A00;
            }
        """)
        self.stop_all_btn.clicked.connect(self._on_stop_all)
        self.auto_btn_layout.addWidget(self.stop_all_btn)
        self.auto_start_btn.setVisible(False)
        self.stop_all_btn.setVisible(False)
        self.auto_btn_layout.addStretch()
        self.vBoxLayout.addLayout(self.auto_btn_layout)

        # Check if this is an imported script to show delete button
        self.imported_file_name = None
        for fn, imp in og.task_manager.imported_scripts.items():
            if imp['script_name'] == self.group_name:
                self.imported_file_name = fn
                break

        if self.imported_file_name:
            from PySide6.QtWidgets import QSpacerItem, QSizePolicy

            self.btn_layout = QHBoxLayout()
            self.btn_layout.setContentsMargins(0, 10, 0, 0)
            self.btn_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

            self.delete_btn = PushButton(self.tr('Delete Script'), self, FluentIcon.DELETE)
            self.delete_btn.clicked.connect(self.delete_script)
            self.btn_layout.addWidget(self.delete_btn)

            # Position it at the end of vBoxLayout
            self.vBoxLayout.addLayout(self.btn_layout)

        from ok.gui.Communicate import communicate
        communicate.task_list_updated.connect(self.refresh_ui)
        self.refresh_ui()

    def _on_stop_all(self):
        """全部停止: 先停当前任务，再禁用其余"""
        og.executor.stop_current_task()
        for task in og.executor.onetime_tasks:
            if task.enabled:
                task.disable()
        logger.info("全部任务已停止")

    def _on_auto_start_all(self):
        """全自动启动: 依次启用所有 启动=True 的任务"""
        import threading
        import time

        tasks_to_run = []
        for task in og.executor.onetime_tasks:
            if task.config.get('_auto_start', True):
                tasks_to_run.append(task)

        if not tasks_to_run:
            logger.info("没有开启自动执行的任务")
            return

        # 记录批次开始时间
        batch_start = time.time()
        batch_start_str = time.strftime('%H:%M:%S', time.localtime(batch_start))
        task_names = [t.name for t in tasks_to_run]
        total_count = len(tasks_to_run)
        completed = {'count': 0}

        def on_task_done(task):
            if task in tasks_to_run:
                completed['count'] += 1
                if completed['count'] >= total_count:
                    batch_end = time.time()
                    batch_end_str = time.strftime('%H:%M:%S', time.localtime(batch_end))
                    duration = batch_end - batch_start
                    mins = int(duration // 60)
                    secs = int(duration % 60)
                    logger.info(f'[全自动] 全部 {total_count} 个任务完成 | 开始: {batch_start_str} | 结束: {batch_end_str} | 总耗时: {mins}分{secs}秒')
                    from ok.gui.Communicate import communicate
                    try:
                        communicate.task_done.disconnect(on_task_done)
                    except (TypeError, RuntimeError):
                        pass

        from ok.gui.Communicate import communicate
        communicate.task_done.connect(on_task_done)

        def _run():
            og.device_manager.do_refresh(True)
            logger.info(f'[全自动] 开始 {total_count} 个任务: {task_names}')
            for task in tasks_to_run:
                if not task.enabled:
                    task.enable()
            og.executor.start()

        threading.Thread(target=_run, name="AutoStart").start()

    def delete_script(self):
        from qfluentwidgets import MessageBox
        w = MessageBox(self.tr('Confirm Delete'), 
                       self.tr('Are you sure you want to delete the script "{}"?').format(self.group_name), 
                       self.window())
        if w.exec():
            og.task_manager.delete_imported_script(self.imported_file_name)

    def refresh_ui(self):
        # Remove old cards
        for w in self.card_widgets:
            self.removeWidget(w)
            w.deleteLater()
        self.card_widgets.clear()

        # If we have a delete button, it's at the end. We need to keep it there.
        if hasattr(self, 'btn_layout'):
            self.vBoxLayout.removeItem(self.btn_layout)

        self.tasks = []
        for task in og.executor.onetime_tasks:
            if not getattr(task, 'visible', True):
                continue
            task_group = getattr(task, 'group_name', None)
            if self.is_standalone and not task_group:
                self.tasks.append(task)
            elif self.group_name and task_group == self.group_name:
                self.tasks.append(task)

        for task in self.tasks:
            task_card = TaskCard(task, True)
            self.card_widgets.append(task_card)
            self.vBoxLayout.addWidget(task_card)

        # 全部开始/停止按钮已移除
        self.auto_start_btn.setVisible(False)
        self.stop_all_btn.setVisible(False)

        if hasattr(self, 'btn_layout'):
            self.vBoxLayout.addLayout(self.btn_layout)

    def in_current_list(self, task):
        return getattr(self, 'tasks', None) and task in self.tasks
