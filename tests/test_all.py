"""
Mi Thermal Editor - Unit and Integration Tests
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from mi_thermal_editor.analyzer import analyze_thermal_config
from mi_thermal_editor.crypto import (
    DEFAULT_IV,
    DEFAULT_KEY,
    batch_decrypt_directory,
    batch_encrypt_directory,
    decrypt_data,
    encrypt_data,
    is_printable_text,
    load_thermal_file,
    save_thermal_file,
)
from mi_thermal_editor.diff_engine import compute_thermal_diff
from mi_thermal_editor.parser import parse_conf, parse_thermal_config


SAMPLE_THERMAL_CONF = """
# Test Xiaomi Thermal Configuration
[BAT_SOC]
algo_type	simulated
path	/sys/class/power_supply/battery/capacity
polling	10000

[VIRTUAL-SENSOR0]
algo_type	Virtual
sensors	cpu_therm	battery	wifi_therm
weight	-26	301	147
polling	2000
weight_sum	1000

[MONITOR-SENSOR0]
algo_type	monitor
sensor	VIRTUAL-SENSOR0
device	VIRTUAL-SENSOR0
polling	1000
trig	25000	30000	35000
clr	23000	27000	32000
target	10000	5000	1000

[SS-CPU0]
algo_type	ss
sensor	VIRTUAL-SENSOR0
device	cpu0
set_point	45000
set_point_clr	43000
time_constant	0
device_perf_floor	1478400
action_type	1
"""

SAMPLE_THERMAL_CONF_MODIFIED = """
# Test Modified Xiaomi Thermal Configuration (Performance Profile)
[BAT_SOC]
algo_type	simulated
path	/sys/class/power_supply/battery/capacity
polling	10000

[VIRTUAL-SENSOR0]
algo_type	Virtual
sensors	cpu_therm	battery	wifi_therm
weight	-26	301	147
polling	2000
weight_sum	1000

[MONITOR-SENSOR0]
algo_type	monitor
sensor	VIRTUAL-SENSOR0
device	VIRTUAL-SENSOR0
polling	1000
trig	30000	35000	40000
clr	28000	32000	37000
target	10000	5000	1000

[SS-CPU0]
algo_type	ss
sensor	VIRTUAL-SENSOR0
device	cpu0
set_point	50000
set_point_clr	47000
time_constant	0
device_perf_floor	1800000
action_type	1

[SS-GPU0]
algo_type	ss
sensor	VIRTUAL-SENSOR0
device	gpu
set_point	60000
set_point_clr	55000
"""


class TestMiThermalEditor(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="thermal_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_crypto_roundtrip(self):
        original_text = SAMPLE_THERMAL_CONF.strip()
        enc_bytes = encrypt_data(original_text)
        self.assertGreater(len(enc_bytes), 0)
        self.assertEqual(len(enc_bytes) % 16, 0)

        dec_text, was_enc = decrypt_data(enc_bytes)
        self.assertTrue(was_enc)
        self.assertEqual(dec_text, original_text)

    def test_is_printable_text(self):
        self.assertTrue(is_printable_text("Hello\n[SECTION]\nalgo_type ss\n"))
        self.assertFalse(is_printable_text("\x00\x01\x02\x03\x04\x05\x06\x07\x08"))
        self.assertFalse(is_printable_text(""))

    def test_file_save_and_load(self):
        test_file = Path(self.temp_dir) / "thermal-normal.conf"
        saved_p, bck_p = save_thermal_file(
            test_file,
            SAMPLE_THERMAL_CONF,
            encrypt=True,
            create_backup=True
        )
        self.assertTrue(os.path.isfile(saved_p))

        loaded = load_thermal_file(saved_p)
        self.assertTrue(loaded.is_encrypted)
        self.assertEqual(loaded.content.strip(), SAMPLE_THERMAL_CONF.strip())

        # Test backup on second save
        saved_p2, bck_p2 = save_thermal_file(
            test_file,
            SAMPLE_THERMAL_CONF_MODIFIED,
            encrypt=True,
            create_backup=True
        )
        self.assertIsNotNone(bck_p2)
        if bck_p2:
            self.assertTrue(os.path.isfile(bck_p2))

    def test_parser(self):
        config = parse_conf(SAMPLE_THERMAL_CONF)
        self.assertEqual(len(config.sections), 4)

        sec_bat = config.get_section("BAT_SOC")
        self.assertIsNotNone(sec_bat)
        if sec_bat:
            self.assertEqual(sec_bat.algo_type, "simulated")

        sec_mon = config.get_section("MONITOR-SENSOR0")
        self.assertIsNotNone(sec_mon)
        if sec_mon:
            self.assertEqual(len(sec_mon.trip_points), 3)
            self.assertEqual(sec_mon.trip_points[0].trigger_temp, 25.0)
            self.assertEqual(sec_mon.trip_points[0].clear_temp, 23.0)

        sec_cpu = config.get_section("SS-CPU0")
        self.assertIsNotNone(sec_cpu)
        if sec_cpu:
            self.assertEqual(sec_cpu.set_point, 45.0)
            self.assertEqual(sec_cpu.set_point_clr, 43.0)

    def test_analyzer(self):
        report = analyze_thermal_config(SAMPLE_THERMAL_CONF, filename="thermal-normal.conf")
        self.assertEqual(report.total_sections, 4)
        self.assertIn("BAT_SOC", report.virtual_sensors)
        self.assertIn("VIRTUAL-SENSOR0", report.virtual_sensors)
        self.assertEqual(report.lowest_throttle_temp, 25.0)
        self.assertEqual(report.highest_throttle_temp, 45.0)
        self.assertIsNotNone(report.matched_sconfig)
        if report.matched_sconfig:
            self.assertEqual(report.matched_sconfig["id"], 0)

    def test_diff_engine(self):
        diff_res = compute_thermal_diff(
            SAMPLE_THERMAL_CONF,
            SAMPLE_THERMAL_CONF_MODIFIED,
            name_a="Stock",
            name_b="Performance"
        )
        self.assertIn("SS-GPU0", diff_res.added_sections)
        self.assertEqual(len(diff_res.removed_sections), 0)
        self.assertTrue(any(s.section_name == "SS-CPU0" for s in diff_res.modified_sections))
        self.assertTrue(len(diff_res.unified_diff_lines) > 0)

    def test_batch_operations(self):
        src_dir = Path(self.temp_dir) / "src_batch"
        dec_dir = Path(self.temp_dir) / "dec_batch"
        enc_dir = Path(self.temp_dir) / "enc_batch"
        src_dir.mkdir()

        # Create encrypted files in src_dir
        for name, text in [("thermal-normal.conf", SAMPLE_THERMAL_CONF), ("thermal-mgame.conf", SAMPLE_THERMAL_CONF_MODIFIED)]:
            fpath = src_dir / name
            save_thermal_file(fpath, text, encrypt=True, create_backup=False)

        # Batch decrypt
        dec_results = batch_decrypt_directory(src_dir, dec_dir)
        self.assertEqual(len(dec_results), 2)
        self.assertTrue(all(is_enc for _, _, is_enc in dec_results))

        # Check plaintext
        with open(dec_dir / "thermal-normal.conf", "r", encoding="utf-8") as f:
            plain_text = f.read()
        self.assertEqual(plain_text.strip(), SAMPLE_THERMAL_CONF.strip())

        # Batch encrypt
        enc_results = batch_encrypt_directory(dec_dir, enc_dir)
        self.assertEqual(len(enc_results), 2)

        # Verify roundtrip
        reloaded = load_thermal_file(enc_dir / "thermal-normal.conf")
        self.assertTrue(reloaded.is_encrypted)
        self.assertEqual(reloaded.content.strip(), SAMPLE_THERMAL_CONF.strip())

    def test_real_xiaomi_thermal_files(self):
        real_odm = Path("/serverhive/yukia/luna/vendor/xiaomi/peridot/proprietary/odm/etc")
        if real_odm.is_dir():
            target = real_odm / "thermal-normal.conf"
            if target.is_file():
                t_file = load_thermal_file(target)
                self.assertTrue(t_file.is_encrypted)
                self.assertIn("BAT_SOC", t_file.content)
                self.assertIn("VIRTUAL-SENSOR0", t_file.content)

                report = analyze_thermal_config(t_file.content, filename=t_file.name)
                self.assertGreater(report.total_sections, 10)
                self.assertIsNotNone(report.matched_sconfig)


if __name__ == "__main__":
    unittest.main()
