import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QTableWidgetItem

from ok import Logger, og
from ok.gui.tasks.TooltipTableWidget import TooltipTableWidget
from ok.gui.widget.Tab import Tab
from ok.gui.widget.UpdateConfigWidgetItem import value_to_string

logger = Logger.get_logger(__name__)


class TaskTab(Tab):
    def __init__(self):
        super().__init__()
        self.keep_info_when_done = False
        self.current_task_name = ""
        self.last_task = None
        self.task_info_table = TooltipTableWidget(width_percentages=[0.3, 0.7])
        self.task_info_table.setFixedHeight(300)
        self.task_info_container = self.add_card(self.tr("Choose Window"), self.task_info_table)
        self.add_widget(self.task_info_container)

        self.task_info_labels = [self.tr('Info'), self.tr('Value')]
        self.task_info_table.setColumnCount(len(self.task_info_labels))  # Name and Value
        self.task_info_table.setHorizontalHeaderLabels(self.task_info_labels)
        self.update_info_table()

        # Create a QTimer object
        self.timer = QTimer()
        self.task_info_container.hide()

        # Connect the timer's timeout signal to the update function
        self.timer.timeout.connect(self.update_info_table)

        # Start the timer with a timeout of 1000 milliseconds (1 second)
        self.timer.start(1000)

    def create_task(self):
        pass

    def in_current_list(self, task):
        return True

    @staticmethod
    def time_elapsed(start_time):
        if start_time > 0:
            # Calculate the difference between the current time and the start time
            elapsed_time = time.time() - start_time

            # Calculate the number of hours, minutes, and seconds
            hours, remainder = divmod(elapsed_time, 3600)
            minutes, seconds = divmod(remainder, 60)

            # Return the elapsed time in the format "1h 12m 5s"
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        else:
            return ""

    def update_info_table(self):
        if og.executor.current_task is not None and self.in_current_list(og.executor.current_task):
            self.last_task = og.executor.current_task
        if og.executor.current_task is None and not self.keep_info_when_done:
            self.task_info_container.hide()
        else:
            self.update_task_info(self.last_task)

    def update_task_info(self, task):
        status = self.tr(
            'Running') if (task is not None and task.enabled) else self.tr('Completed')
        self.task_info_container.titleLabel.setText(
            status + self.current_task_name)
        if task is None or time.time() - task.start_time < 2:
            return
        if not self.task_info_table.isVisible():
            self.task_info_container.show()

        info = task.info
        if task.enabled:
            self.current_task_name = f": {og.app.tr(task.name)} {self.tr('Time Elapsed')}: {self.time_elapsed(task.start_time)}"

        # 构建表格行: info 行 + 开始/结束时间行
        st = getattr(task, '_run_start', 0)
        et = getattr(task, '_run_end', 0)
        extra_rows = []
        if st > 0:
            extra_rows.append((self.tr("开始时间"), time.strftime('%H:%M:%S', time.localtime(st))))
        if et > 0:
            extra_rows.append((self.tr("结束时间"), time.strftime('%H:%M:%S', time.localtime(et))))

        total_rows = len(info) + len(extra_rows)
        self.task_info_table.setRowCount(total_rows)
        row = 0
        for key, value in info.items():
            if not self.task_info_table.item(row, 0):
                self.task_info_table.setItem(row, 0, self.uneditable_item())
            self.task_info_table.item(row, 0).setText(og.app.tr(key))
            if not self.task_info_table.item(row, 1):
                self.task_info_table.setItem(row, 1, self.uneditable_item())
            self.task_info_table.item(row, 1).setText(og.app.tr(value_to_string(value)))
            row += 1
        for key, value in extra_rows:
            if not self.task_info_table.item(row, 0):
                self.task_info_table.setItem(row, 0, self.uneditable_item())
            self.task_info_table.item(row, 0).setText(key)
            if not self.task_info_table.item(row, 1):
                self.task_info_table.setItem(row, 1, self.uneditable_item())
            self.task_info_table.item(row, 1).setText(value)
            row += 1

    def uneditable_item(self):
        item = QTableWidgetItem()
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item
