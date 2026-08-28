from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel, QSplitter)
from PySide6.QtCore import Qt

from ..core.analyzer import analyze_thermal_config

class AnalyzerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_info = QLabel("Select a file to parse and analyze.")
        self.lbl_info.setStyleSheet("padding: 8px; font-weight: bold; font-size: 11pt; color: #03DAC6;")
        layout.addWidget(self.lbl_info)
        
        splitter = QSplitter(Qt.Vertical)
        
        # Sensors
        self.tree_sensors = QTreeWidget()
        self.tree_sensors.setHeaderLabels(["Sensor", "Type", "Min Temp (°C)", "Max Temp (°C)"])
        splitter.addWidget(self.tree_sensors)
        
        # Mitigations
        self.tree_mitigations = QTreeWidget()
        self.tree_mitigations.setHeaderLabels(["Device", "Rule / Section", "Trigger (°C)", "Clear (°C)", "Action"])
        splitter.addWidget(self.tree_mitigations)
        
        layout.addWidget(splitter)

    def analyze_content(self, content, filename):
        try:
            report = analyze_thermal_config(content, filename=filename)
            self.tree_sensors.clear()
            self.tree_mitigations.clear()
            
            sconfig_info = f" | SCONFIG [{report.matched_sconfig['id']}]: {report.matched_sconfig['name']}" if report.matched_sconfig else ""
            self.lbl_info.setText(f"Analysis: {filename}{sconfig_info}")
            
            for s in report.sensors:
                item = QTreeWidgetItem([
                    s.sensor_name,
                    "Virtual" if s.is_virtual else "Physical",
                    f"{s.min_trigger_temp:.1f}" if s.min_trigger_temp is not None else "-",
                    f"{s.max_trigger_temp:.1f}" if s.max_trigger_temp is not None else "-"
                ])
                self.tree_sensors.addTopLevelItem(item)
                
            for d in report.devices:
                for rule in d.trip_points:
                    item = QTreeWidgetItem([
                        d.device_name,
                        rule["section"],
                        f"{rule['trigger']:.1f}" if rule['trigger'] is not None else "-",
                        f"{rule['clear']:.1f}" if rule['clear'] is not None else "-",
                        str(rule["action"]) if rule["action"] else "-"
                    ])
                    self.tree_mitigations.addTopLevelItem(item)
                    
            for i in range(4): self.tree_sensors.resizeColumnToContents(i)
            for i in range(5): self.tree_mitigations.resizeColumnToContents(i)
        except Exception as e:
            self.lbl_info.setText(f"Failed to analyze: {str(e)}")
